"""RAG по собственному коду Капри: обходит свои исходники, режет на куски, считает эмбеддинги (CPU)
и ищет по смыслу. Индекс кэшируется на диске и пересобирается, только если файлы изменились.

Только чтение. Нужен, чтобы Капри отвечала о себе по реальному коду, а не выдумывала."""
import ast
import json
import logging
import os
import threading
from typing import Any

from src.application.assistant.interfaces.i_code_rag_adapter import ICodeRagAdapter
from src.application.assistant.interfaces.i_embedding_adapter import IEmbeddingAdapter

log = logging.getLogger("capri")

INDEX_DIRNAME = ".capri_rag"       # папка кэша индекса в корне проекта
SCAN_DIRS = ("src",)               # что индексируем (её собственный код)
EXTRA_FILES = ("README.md", "requirements.txt")
CHUNK_LINES = 40                   # размер куска в строках (для не-Python и переразбивки больших блоков)
OVERLAP_LINES = 10                 # нахлёст соседних кусков, чтобы не рвать мысль на границе
MAX_CHUNK_CHARS = 4000             # слишком большой блок (функция/класс) переразбиваем окнами
MAX_FILE_BYTES = 200_000           # очень большие файлы пропускаем
INDEX_VERSION = 2                  # меняем при смене алгоритма нарезки/эмбеддинга — старый кэш инвалидируется
# шумовые слова запроса — выкидываем из лексического поиска, чтобы доминировала суть («микрофон», «comfyui»)
STOPWORDS = frozenset((
    "как", "что", "про", "где", "кто", "это", "так", "там", "тут", "для", "или", "под", "над", "при",
    "твой", "твоя", "твоё", "твое", "твоём", "твоем", "твои", "твоих", "тебя", "тебе", "себя", "себе",
    "коде", "код", "ты", "вот", "его", "её", "они", "оно", "мне", "нам", "весь", "вся", "всё", "все",
    "работает", "устроен", "устроена", "сделан", "сделана", "есть", "быть", "может", "можешь", "умеешь",
))


class CodeRagAdapter(ICodeRagAdapter):
    def __init__(self, embedding: IEmbeddingAdapter, base_dir: str, settings: dict[str, Any]) -> None:
        self._emb = embedding
        self._root = base_dir
        self._index_dir = os.path.join(base_dir, INDEX_DIRNAME)
        self._lock = threading.Lock()
        self._vectors = None        # np.ndarray (N, dim), нормированные
        self._metas: list[dict[str, Any]] = []
        self._ready = False

    # ---------- сбор файлов ----------
    def _iter_files(self):
        for sub in SCAN_DIRS:
            root = os.path.join(self._root, sub)
            for dirpath, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", INDEX_DIRNAME, ".git", ".venv")]
                for name in files:
                    if name.endswith(".py"):
                        yield os.path.join(dirpath, name)
        for name in EXTRA_FILES:
            path = os.path.join(self._root, name)
            if os.path.isfile(path):
                yield path

    def _rel(self, path: str) -> str:
        return os.path.relpath(path, self._root).replace("\\", "/")

    def _fingerprint(self, files: list[str]) -> dict[str, list[float]]:
        # версия + модель эмбеддингов в отпечатке: сменилось — старый кэш не подойдёт
        fp: dict[str, Any] = {"__version__": [INDEX_VERSION, 0]}
        for f in files:
            try:
                st = os.stat(f)
                fp[self._rel(f)] = [st.st_mtime, st.st_size]
            except OSError:
                continue
        return fp

    def _window_chunks(self, lines: list[str], base: int = 0, label: str = ""):
        """Нарезка окнами по строкам — для не-Python файлов и очень больших блоков."""
        step = max(1, CHUNK_LINES - OVERLAP_LINES)
        for start in range(0, len(lines), step):
            block = "".join(lines[start:start + CHUNK_LINES]).strip("\n")
            if block.strip():
                text = (label + "\n" + block) if label else block
                yield base + start + 1, text

    def _chunk_file(self, path: str):
        """Python режем по структуре (каждая функция/метод/класс — отдельный кусок с меткой
        «файл :: Класс.метод»), остальное — окнами. Так поиск попадает в нужное место, а не в середину."""
        rel = self._rel(path)
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                return
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            return
        lines = src.splitlines(keepends=True)
        if not path.endswith(".py"):
            yield from self._window_chunks(lines, label=rel)
            return
        try:
            tree = ast.parse(src)
        except SyntaxError:
            yield from self._window_chunks(lines, label=rel)
            return

        def segment(node) -> tuple[int, str]:
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            return start, "".join(lines[start - 1:end])

        def emit(node, label: str):
            start, body = segment(node)
            head = "%s :: %s" % (rel, label)
            if len(body) <= MAX_CHUNK_CHARS:
                yield start, head + "\n" + body
            else:  # большая функция/метод — переразбиваем окнами, но с той же меткой
                yield from self._window_chunks(body.splitlines(keepends=True), base=start - 1, label=head)

        covered: set[int] = set()

        def cover(node):
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            covered.update(range(node.lineno, end + 1))

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from emit(node, node.name + "()")
                cover(node)
            elif isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                # шапка класса: от «class …» до первого метода (докстринг, атрибуты) — отдельным куском
                head_end = (methods[0].lineno - 1) if methods else (getattr(node, "end_lineno", node.lineno))
                head_body = "".join(lines[node.lineno - 1:head_end]).strip("\n")
                if head_body.strip():
                    yield node.lineno, "%s :: class %s\n%s" % (rel, node.name, head_body)
                for mth in methods:
                    yield from emit(mth, "%s.%s()" % (node.name, mth.name))
                cover(node)

        # всё, что вне функций/классов (импорты, константы, таблицы маршрутов) — окнами по незанятым строкам
        gap: list[str] = []
        gap_start = 0
        for i, line in enumerate(lines, start=1):
            if i in covered:
                if gap:
                    yield from self._window_chunks(gap, base=gap_start, label="%s :: модуль" % rel)
                    gap = []
            else:
                if not gap:
                    gap_start = i - 1
                gap.append(line)
        if gap:
            yield from self._window_chunks(gap, base=gap_start, label="%s :: модуль" % rel)

    # ---------- построение индекса ----------
    def build(self, force: bool = False) -> bool:
        with self._lock:
            if self._ready and not force:
                return True
            if not self._emb.available:
                log.info("RAG по коду: модель эмбеддингов недоступна — индекс не строю")
                return False
            files = list(self._iter_files())
            fp = self._fingerprint(files)
            if not force and self._load_cache(fp):
                self._ready = True
                log.info("RAG по коду: индекс взят из кэша (%d кусков)", len(self._metas))
                return True
            texts, metas = [], []
            for f in files:
                rel = self._rel(f)
                for start, block in self._chunk_file(f):
                    texts.append(block)
                    metas.append({"file": rel, "start": start, "text": block})
            if not texts:
                return False
            log.info("RAG по коду: считаю эмбеддинги для %d кусков из %d файлов…", len(texts), len(files))
            vectors = self._emb.embed(texts)
            if not vectors:
                return False
            import numpy as np
            mat = np.vstack(vectors).astype(np.float32)
            mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)   # нормируем → косинус = скалярное
            self._vectors, self._metas, self._ready = mat, metas, True
            self._save_cache(fp)
            log.info("RAG по коду: индекс готов (%d кусков)", len(metas))
            return True

    # ---------- кэш на диске ----------
    def _load_cache(self, fp: dict) -> bool:
        try:
            import numpy as np
            with open(os.path.join(self._index_dir, "fingerprint.json"), encoding="utf-8") as fh:
                if json.load(fh) != fp:
                    return False
            with open(os.path.join(self._index_dir, "meta.json"), encoding="utf-8") as fh:
                self._metas = json.load(fh)
            self._vectors = np.load(os.path.join(self._index_dir, "vectors.npy"))
            return len(self._metas) == self._vectors.shape[0]
        except (OSError, ValueError, KeyError):
            return False

    def _save_cache(self, fp: dict) -> None:
        try:
            import numpy as np
            os.makedirs(self._index_dir, exist_ok=True)
            np.save(os.path.join(self._index_dir, "vectors.npy"), self._vectors)
            with open(os.path.join(self._index_dir, "meta.json"), "w", encoding="utf-8") as fh:
                json.dump(self._metas, fh, ensure_ascii=False)
            with open(os.path.join(self._index_dir, "fingerprint.json"), "w", encoding="utf-8") as fh:
                json.dump(fp, fh, ensure_ascii=False)
        except OSError as e:
            log.info("RAG по коду: не удалось сохранить кэш: %s", e)

    # ---------- поиск ----------
    def is_ready(self) -> bool:
        return self._ready

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        if not self._ready or self._vectors is None:
            return []
        vecs = self._emb.embed([query])
        if not vecs:
            return []
        import re

        import numpy as np
        q = vecs[0].astype(np.float32)
        q /= (np.linalg.norm(q) + 1e-8)
        sims = self._vectors @ q
        # гибрид: к семантике добавляем лексику — доля слов запроса, встреченных в куске кода.
        # Конкретные термины (comfyui, загрузк, теги) так находятся точно, а не «по смыслу мимо».
        terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3 and t not in STOPWORDS}
        if terms:
            lex = np.array([sum(t in m["text"].lower() for t in terms) / len(terms)
                            for m in self._metas], dtype=np.float32)
            scores = sims + 0.6 * lex
        else:
            scores = sims
        top = np.argsort(-scores)[:max(1, k)]
        return [{**self._metas[i], "score": float(scores[i])} for i in top]

    def stats(self) -> dict[str, Any]:
        modules = sorted({m["file"].split("/")[1] for m in self._metas if m["file"].startswith("src/")
                          and len(m["file"].split("/")) > 2})
        files = sorted({m["file"] for m in self._metas})
        return {"ready": self._ready, "files": len(files), "chunks": len(self._metas), "modules": modules}
