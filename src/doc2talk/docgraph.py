# Chat: https://chat.deepseek.com/a/chat/s/3ab8f236-445b-4892-b3d9-13d19ddb5e63

import time
import ast
import hashlib
import fnmatch
from pathlib import Path
import re
from collections import defaultdict
from math import log
import subprocess
import shutil
from abc import ABC, abstractmethod
import msgpack
import struct
import zstandard as zstd
import mmap


class ResourcePathResolver(ABC):
    @abstractmethod
    def validate(self, path: str = None) -> bool:
        pass
    
    @abstractmethod
    def resolve(self, path: str = None) -> tuple[Path, Path]:
        pass

class LocalResolver(ResourcePathResolver):
    def validate(self, path: str = None) -> bool:
        code = Path(path).exists()
        return bool(code)
        
    def resolve(self, path: str = None) -> tuple[Path, Path]:
        root = Path(path)
        return root

class GitHubResolver(ResourcePathResolver):
    # Define constants
    REPOS_DIR = Path.home() / ".doctalk" / "repos"
    MAX_REPO_AGE_DAYS = 30  # Auto cleanup repos older than this
    
    def __init__(self):
        self.temp_dirs = []
        self.cached_repos = []
        
        # Create cache directory if it doesn't exist
        self.REPOS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Perform cleanup of old repos on init (if needed)
        self._cleanup_old_repos()
        
    def validate(self, path: str, *args) -> bool:
        if not isinstance(path, str):
            return False
        return bool(re.match(r'^(https?://github\.com/|git@github\.com:)', path))
    
    def resolve(self, path: str, *args) -> Path:
        repo_info = self._parse_github_url(path)
        return self._fetch_repo_content(repo_info)
    
    def _parse_github_url(self, url: str) -> dict:
        """Parse GitHub URL into components"""
        pattern = r'github\.com[:/](?P<user>[^/]+)/(?P<repo>[^/]+)(/tree/(?P<branch>[^/]+))?(?P<path>/.+)?'
        match = re.search(pattern, url)
        if not match:
            raise ValueError(f"Invalid GitHub URL format: {url}")
            
        info = match.groupdict()
        info['repo'] = info['repo'].replace('.git', '')
        info['branch'] = info['branch'] or 'main'
        info['path'] = (info['path'] or '').strip('/')
        return info
    
    def _cleanup_old_repos(self):
        """Clean up repositories that haven't been accessed in a long time"""
        import time
        
        # Skip if disabled
        if self.MAX_REPO_AGE_DAYS <= 0:
            return
            
        current_time = time.time()
        cutoff_time = current_time - (self.MAX_REPO_AGE_DAYS * 24 * 60 * 60)
        
        # Check all repositories in cache
        for repo_dir in self.REPOS_DIR.iterdir():
            if not repo_dir.is_dir():
                continue
                
            # Check last access time
            access_file = repo_dir / ".last_access"
            if not access_file.exists():
                # No access record, use directory creation time
                last_access = repo_dir.stat().st_mtime
            else:
                try:
                    last_access = float(access_file.read_text().strip())
                except:
                    last_access = repo_dir.stat().st_mtime
            
            # Remove if too old
            if last_access < cutoff_time:
                try:
                    shutil.rmtree(repo_dir)
                    print(f"Cleaned up old repo: {repo_dir.name}")
                except Exception as e:
                    print(f"Warning: Failed to clean up old repo {repo_dir}: {e}")
    
    def _get_repo_cache_path(self, repo_info: dict) -> Path:
        """Get path to cached repository, incorporating the requested path"""
        # Base repo info
        repo_base = f"{repo_info['user']}_{repo_info['repo']}_{repo_info['branch']}"
        repo_name = repo_base

        return self.REPOS_DIR / f"{repo_name}"
        
        # Add path hash to differentiate between different paths in same repo
        # if repo_info['path']:
        #     path_hash = hashlib.md5(repo_info['path'].encode()).hexdigest()[:6]
        #     repo_name = f"{repo_base}_{path_hash}"
        # else:
        #     repo_name = repo_base
            
        # repo_hash = hashlib.md5(repo_name.encode()).hexdigest()[:10]
        # return self.REPOS_DIR / f"{repo_name}_{repo_hash}"
    
    def _update_access_time(self, repo_path: Path):
        """Update the last access time for a repository"""
        access_file = repo_path / ".last_access"
        access_file.write_text(str(time.time()))
    
    def _fetch_repo_content(self, repo_info: dict) -> Path:
        try:
            """Fetch repository content using cache when possible"""
            repo_cache_path = self._get_repo_cache_path(repo_info)
            self.cached_repos.append(repo_cache_path)
            
            repo_url = f"https://github.com/{repo_info['user']}/{repo_info['repo']}.git"
            target_path = repo_cache_path / repo_info['path'] if repo_info['path'] else repo_cache_path
            
            # Check if repo is already cached AND the target path exists
            if repo_cache_path.exists() and (repo_cache_path / ".git").exists() and target_path.exists():
                print(f"Using cached repository: {repo_info['user']}/{repo_info['repo']} (path: {repo_info['path'] or 'root'})")
                
                # Update the repository
                try:
                    subprocess.run(['git', 'pull', 'origin', repo_info['branch']], 
                                cwd=repo_cache_path, check=True, capture_output=True)
                    
                    # If using sparse-checkout, make sure the path is in the sparse-checkout file
                    if repo_info['path']:
                        sparse_file = repo_cache_path / '.git/info/sparse-checkout'
                        if sparse_file.exists():
                            current_paths = sparse_file.read_text().strip().split('\n')
                            if repo_info['path'] not in current_paths:
                                sparse_file.write_text('\n'.join(current_paths + [repo_info['path']]))
                                # Update checkout for new sparse-checkout paths
                                subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], 
                                            cwd=repo_cache_path, check=True, capture_output=True)
                except Exception as e:
                    print(f"Warning: Failed to update cached repo: {e}")
                    
                # Update access time
                self._update_access_time(repo_cache_path)
            else:
                # Either repo doesn't exist or the specific path doesn't exist
                if repo_cache_path.exists() and (repo_cache_path / ".git").exists():
                    # Repo exists but target path doesn't - update sparse checkout
                    print(f"Updating existing repository to include: {repo_info['path']}")
                    
                    # Enable sparse checkout if not already enabled
                    subprocess.run(['git', 'config', 'core.sparseCheckout', 'true'], 
                                cwd=repo_cache_path, check=True, capture_output=True)
                    
                    # Add the new path to sparse-checkout
                    sparse_file = repo_cache_path / '.git/info/sparse-checkout'
                    if sparse_file.exists():
                        current_paths = sparse_file.read_text().strip().split('\n')
                        if repo_info['path'] not in current_paths:
                            sparse_file.write_text('\n'.join([p for p in current_paths if p] + [repo_info['path']]))
                    else:
                        sparse_file.write_text(repo_info['path'])
                    
                    # Update checkout for sparse-checkout
                    subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], 
                                cwd=repo_cache_path, check=True, capture_output=True)
                else:
                    # Clone fresh repository
                    print(f"Cloning repository: {repo_info['user']}/{repo_info['repo']}")
                    
                    # Create parent directory
                    repo_cache_path.mkdir(parents=True, exist_ok=True)
                    
                    # Clone the repository
                    subprocess.run(['git', 'clone', '--branch', repo_info['branch'], 
                                repo_url, str(repo_cache_path)], check=True, capture_output=True)
                    
                    # Enable sparse checkout if path is specified
                    if repo_info['path']:
                        subprocess.run(['git', 'config', 'core.sparseCheckout', 'true'], 
                                    cwd=repo_cache_path, check=True, capture_output=True)
                        sparse_file = repo_cache_path / '.git/info/sparse-checkout'
                        sparse_file.write_text(repo_info['path'])
                        
                        # Update checkout for sparse-checkout
                        subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], 
                                    cwd=repo_cache_path, check=True, capture_output=True)
                
                # Update access time
                self._update_access_time(repo_cache_path)
            
            # Verify the target path exists after all operations
            if not target_path.exists():
                raise ValueError(f"Path not found in repository: {repo_info['path']}")
                
            return target_path
            
        except Exception as e:
            # No cleanup needed for cache failures
            raise e
    
    def cleanup(self):
        """Temporary dirs still need cleanup"""
        for temp_dir in self.temp_dirs:
            if Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
        
        # We don't clean up cached repos here, they'll be auto-cleaned based on access time

class KnowledgeGraph:
    def __init__(self):
        self.nodes = {}
        self.graph = defaultdict(list)
        self.index = defaultdict(list)
        self.class_registry = {}
        self.function_registry = {}
        self.parent_map = {}
        self.documents = []

    def add_node(self, content, meta):
        node_id = hashlib.sha256(content.encode()).hexdigest()
        self.nodes[node_id] = {'content': content, 'meta': meta}
        self.documents.append(content)
        
        # Index node type
        if meta['type'] == 'py':
            name = meta.get('name', '').lower()
            if meta['node_type'] == 'class':
                self.class_registry[name] = node_id
            elif meta['node_type'] == 'function':
                self.function_registry[name] = node_id
                if meta['parent']:
                    self.parent_map[node_id] = meta['parent'].lower()

        # Index content
        for token in self.tokenize(content):
            self.index[token].append(node_id)
        
        return node_id

    def tokenize(self, text):
        return re.findall(r'\b\w+\b', text.lower())

    def bm25_search(self, query, top_n=3, exclude_types=None):
        tokens = self.tokenize(query)
        scores = defaultdict(float)
        avgdl = sum(len(d.split()) for d in self.documents) / len(self.documents)
        N = len(self.documents)
        k1, b = 1.5, 0.75

        for token in tokens:
            df = len(self.index.get(token, []))
            if df == 0:
                continue
            idf = log((N - df + 0.5) / (df + 0.5) + 1)
            for node_id in self.index[token]:
                node = self.nodes[node_id]
                if exclude_types and node['meta'].get('node_type') in exclude_types:
                    continue
                doc = node['content']
                tf = doc.lower().count(token)
                dl = len(doc.split())
                score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
                scores[node_id] += score

        return sorted(scores.items(), key=lambda x: -x[1])[:top_n]  # Now properly using top_n

class Chunker:
    @staticmethod
    def chunk_markdown(content, path, min_section_level=2):
        # Convert path to string for serialization
        path_str = str(path) if isinstance(path, Path) else path
        # Split at heading levels equal to or greater than min_section_level
        heading_pattern = rf'(?=^#{{{min_section_level},}} )'
        chunks = re.split(heading_pattern, content, flags=re.MULTILINE)
        return [{
            'content': chunk.strip(),
            'meta': {
                'type': 'md', 
                'path': path_str,  # Store as string
                'node_type': 'section',
                'parent': None,
                'full_content': content  # Store original for potential replacement
            }
        } for chunk in chunks if chunk.strip()]

    @staticmethod
    def chunk_python(content, path):
        # Convert path to string for serialization
        path_str = str(path) if isinstance(path, Path) else path
        chunks = []
        tree = ast.parse(content)
        
        class Collector(ast.NodeVisitor):
            def __init__(self):
                self.stack = []
                self.current_class = None
            
            def visit_ClassDef(self, node):
                self.current_class = node.name.lower()
                chunk = {
                    'content': ast.get_source_segment(content, node),
                    'meta': {
                        'type': 'py',
                        'node_type': 'class',
                        'name': node.name,
                        'path': path_str,  # Store as string
                        'line': node.lineno,
                        'parent': ' > '.join(self.stack) if self.stack else None
                    }
                }
                chunks.append(chunk)
                self.stack.append(f'class {node.name}')
                self.generic_visit(node)
                self.stack.pop()
                self.current_class = None

            def visit_FunctionDef(self, node):
                chunk = {
                    'content': ast.get_source_segment(content, node),
                    'meta': {
                        'type': 'py',
                        'node_type': 'function',
                        'name': node.name,
                        'path': path_str,  # Store as string
                        'line': node.lineno,
                        'parent': self.current_class
                    }
                }
                chunks.append(chunk)
                self.stack.append(f'def {node.name}')
                self.generic_visit(node)
                self.stack.pop()

        Collector().visit(tree)
        return chunks

class DocGraph:
    RESOLVERS = [
        LocalResolver(),
        GitHubResolver()
    ]
    
    # Add class constants
    _CACHE_VERSION = 2
    _MAGIC_HEADER = b'C4AIV2'
    _COMPRESS_LEVEL = 3  # Balanced speed/ratio

    def __init__(self, code_source=None, docs_source=None, exclude=None):
        # Add initialization flags
        self._from_cache = False
        self._mmap = None
        
        # Rest of original __init__ code
        if code_source is None and docs_source is None:
            raise ValueError("At least one of code_source or docs_source must be provided")
            
        self.graph = KnowledgeGraph()
        self.exclude = exclude or []
        
        # Only build if not loading from cache
        if not self._from_cache:
            self._setup_paths(code_source, docs_source)
            self._build_graph()

    def _setup_paths(self, code_source, docs_source):
        """Setup paths handling mixed local and remote sources"""
        self.resolvers = []
        
        # Resolve code source if provided
        if code_source:
            code_resolver = self._get_resolver(code_source)
            self.code_root = code_resolver.resolve(code_source)
            self.resolvers.append(code_resolver)
        
        # Resolve docs source if provided
        if docs_source:
            docs_resolver = self._get_resolver(docs_source)
            self.docs_root = docs_resolver.resolve(docs_source)
            if docs_resolver != code_resolver:
                self.resolvers.append(docs_resolver)
        
        # Ensure at least one path is set
        if not hasattr(self, 'code_root') and not hasattr(self, 'docs_root'):
            raise ValueError("Failed to resolve any valid paths")

    def _get_resolver(self, path):
        """Get appropriate resolver for the given path"""
        for resolver in self.RESOLVERS:
            if resolver.validate(path):
                return resolver
        raise ValueError(f"No valid resolver found for: {path}")
    
    def __del__(self):
        """Cleanup mmap when destroyed"""
        if hasattr(self, '_mmap') and self._mmap:
            self._mmap.close()
        # Rest of original cleanup
        for resolver in getattr(self, 'resolvers', []):
            if hasattr(resolver, 'cleanup'):
                resolver.cleanup()          

    def persist(self, path):
        """Save optimized index format"""
        # Convert Path objects to strings
        state = {
            'graph': {
                'nodes': self.graph.nodes,
                'graph': self.graph.graph,
                'index': self.graph.index,
                'class_registry': self.graph.class_registry,
                'function_registry': self.graph.function_registry,
                'parent_map': self.graph.parent_map,
                'documents': self.graph.documents
            },
            'code_root': str(self.code_root) if hasattr(self, 'code_root') else None,
            'docs_root': str(self.docs_root) if hasattr(self, 'docs_root') else None,
            'exclude': self.exclude,
            'version': self._CACHE_VERSION
        }

        # Use compressed MessagePack format
        cctx = zstd.ZstdCompressor(level=self._COMPRESS_LEVEL)
        packed = msgpack.packb(state)
        compressed = cctx.compress(packed)
        
        with open(path, 'wb') as f:
            f.write(self._MAGIC_HEADER)
            f.write(struct.pack('!I', self._CACHE_VERSION))
            f.write(struct.pack('!Q', len(compressed)))
            f.write(compressed)

    @classmethod
    def load(cls, path):
        """Ultra-fast mmap-based loading"""
        with open(path, 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            
            # Verify header
            if mm[:len(cls._MAGIC_HEADER)] != cls._MAGIC_HEADER:
                raise ValueError("Invalid cache format")
                
            version = struct.unpack('!I', mm[6:10])[0]
            if version != cls._CACHE_VERSION:
                raise ValueError("Cache version mismatch")
                
            data_size = struct.unpack('!Q', mm[10:18])[0]
            compressed = mm[18:18+data_size]
            
        # Decompress and unpack
        dctx = zstd.ZstdDecompressor()
        packed = dctx.decompress(compressed)
        state = msgpack.unpackb(packed)

        # Reconstruct object
        instance = cls.__new__(cls)
        instance._from_cache = True
        instance._mmap = mm  # Keep mmap reference
        
        # Rebuild KnowledgeGraph
        instance.graph = KnowledgeGraph()
        instance.graph.nodes = state['graph']['nodes']
        instance.graph.graph = state['graph']['graph']
        instance.graph.index = state['graph']['index']
        instance.graph.class_registry = state['graph']['class_registry']
        instance.graph.function_registry = state['graph']['function_registry']
        instance.graph.parent_map = state['graph']['parent_map']
        instance.graph.documents = state['graph']['documents']
        
        # Convert string paths back to Path objects
        if state['code_root']:
            instance.code_root = Path(state['code_root'])
        if state['docs_root']:
            instance.docs_root = Path(state['docs_root'])
            
        instance.exclude = state['exclude']
        
        return instance

    def _is_excluded(self, path):
        path_str = str(path)
        return any(fnmatch.fnmatch(path_str, pattern) for pattern in self.exclude)

    def _build_graph(self):
        # Process code
        for py_path in self.code_root.rglob('*.py'):
            if self._is_excluded(py_path):
                continue
            chunks = Chunker.chunk_python(py_path.read_text(), py_path)
            self._add_to_graph(chunks)
            
        # Process documentation
        for md_path in self.docs_root.rglob('*.md'):
            if self._is_excluded(md_path):
                continue
            chunks = Chunker.chunk_markdown(md_path.read_text(), md_path)
            self._add_to_graph(chunks)

    def _add_to_graph(self, chunks):
        node_relations = {}
        for chunk in chunks:
            node_id = self.graph.add_node(chunk['content'], chunk['meta'])
            
            # Link markdown to classes
            if chunk['meta']['type'] == 'md':
                for token in self.graph.tokenize(chunk['content']):
                    if class_id := self.graph.class_registry.get(token):
                        self.graph.graph[node_id].append(class_id)

            # Track parent relationships
            if chunk['meta'].get('parent'):
                node_relations[chunk['meta']['name'].lower()] = node_id

    def query(self, question, top_n=10, top_m=3, file_coverage=0.6):
        doc_nodes = self.graph.bm25_search(question, top_n=top_n, exclude_types={'class', 'function'})
        class_nodes = self._find_related_classes(doc_nodes, question)
        result = self._format_results(doc_nodes[:top_n], class_nodes[:top_m], [], file_coverage)
        # print(f"BM25 search: {t1-t0:.3f}s")
        # print(f"Find classes: {t2-t1:.3f}s")
        # print(f"Format results: {t3-t2:.3f}s")
        return result
        
        # return self._format_results(doc_nodes[:top_n], class_nodes[:top_m], functions, file_coverage)

    def _bm25_score(self, query, documents):
        """Generic BM25 scoring for arbitrary documents"""
        tokens = self.graph.tokenize(query)
        scores = defaultdict(float)
        avgdl = sum(len(d[1].split()) for d in documents) / len(documents)
        N = len(documents)
        k1, b = 1.5, 0.75

        # Document frequency calculation
        df = defaultdict(int)
        for _, content in documents:
            seen = set()
            for token in self.graph.tokenize(content):
                if token not in seen:
                    df[token] += 1
                    seen.add(token)

        # Score calculation
        for cid, content in documents:
            doc_tokens = self.graph.tokenize(content)
            dl = len(doc_tokens)
            for token in tokens:
                if token not in df:
                    continue
                tf = doc_tokens.count(token)
                idf = log((N - df[token] + 0.5) / (df[token] + 0.5) + 1)
                score = idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
                scores[cid] += score

        return scores

    def _find_related_classes(self, doc_nodes, query):
        # Get initial class connections
        class_candidates = set()
        doc_scores = {nid: score for nid, score in doc_nodes}
        for node_id, _ in doc_nodes:
            class_candidates.update(self.graph.graph[node_id])
            
        if not class_candidates:
            return []

        # Score classes using their own content BM25
        class_contents = [
            (cid, self.graph.nodes[cid]['content']) 
            for cid in class_candidates
        ]
        class_scores = self._bm25_score(query, class_contents)
        
        # Scale down the class_scores by the max score
        max_score = max(class_scores.values())
        class_scores = {k: v / max_score for k, v in class_scores.items()}
        
        # Extract [(doc_id, score)] pairs
        doc_nodes = [(nid, score) for nid, score in doc_nodes]
        # Scale down the doc_nodes scores by the max score
        max_score = max(doc_scores.values())
        doc_scores = [(nid, score / max_score) for nid, score in doc_nodes]
        
        # Calculate documentation mention scores
        doc_mention_scores = defaultdict(float)
        for cid in class_candidates:
            for doc_node_id, score in doc_scores:
                if cid in self.graph.graph[doc_node_id]:
                    doc_mention_scores[cid] += score * 0.7  # Base documentation weight
                    
        # # scale down the doc_mention_scores by the max score
        max_score = max(doc_mention_scores.values())
        doc_mention_scores = {k: v / max_score for k, v in doc_mention_scores.items()}

        # Dynamic combination with non-linear scaling
        combined = defaultdict(float)
        data = []
        for cid in class_candidates:
            bm25 = class_scores.get(cid, 0)
            docs_score = doc_mention_scores.get(cid, 0)
            
            # Dynamic dampening factor based on BM25 score magnitude
            dampening = 1 / (1 + abs(bm25) ** 1.5)  # Quadratic dampening
            combined[cid] = bm25 + (docs_score * dampening)
            data.append((cid, bm25, docs_score, dampening, combined[cid]))

        return sorted(combined.items(), key=lambda x: -x[1])

    def _format_results(self, doc_nodes, class_nodes, function_nodes, file_coverage=0.6):
        # Group document nodes by their source file
        file_map = defaultdict(list)
        for node_id, score in doc_nodes:
            node = self.graph.nodes[node_id]
            file_map[node['meta']['path']].append(node)

        # Apply file coverage threshold
        final_docs = []
        for path, nodes in file_map.items():
            try:
                full_content = nodes[0]['meta']['full_content']
                total_chunks = len(Chunker.chunk_markdown(full_content, path))
                selected_chunks = len(nodes)
                
                if selected_chunks / total_chunks >= file_coverage:
                    final_docs.append({
                        'content': full_content,
                        'meta': {'path': path, 'full_file': True}
                    })
                else:
                    final_docs.extend(nodes)
            except Exception:
                final_docs.extend(nodes)

        # Build output structure
        output = ["# Documentation Context\n"]
        
        # Add documentation sections
        for node in final_docs[:len(doc_nodes)]:  # Respect original top_n count
            # Get path name from string or Path object
            path = node['meta']['path']
            path_name = Path(path).name if isinstance(path, str) else path.name
            
            if node.get('meta', {}).get('full_file'):
                header = f"## FULL FILE: {path_name}"
                content = node['content']
            else:
                header = f"## {path_name}"
                content = node['content']
            output.append(f"{header}\n```markdown\n{content}\n```")

        # Add class appendix
        if class_nodes:
            output.append("\n# Related Classes\n")
            for class_id, score in class_nodes:
                node = self.graph.nodes[class_id]
                output.append(f"## {node['meta']['name']}\n```python\n{node['content']}\n```")

        # Add function appendix
        if function_nodes:
            output.append("\n# Related Functions\n")
            for func_id, score in function_nodes:
                node = self.graph.nodes[func_id]
                parent = f" ({node['meta']['parent']})" if node['meta']['parent'] else ""
                output.append(f"## {node['meta']['name']}{parent}\n```python\n{node['content']}\n```")

        return "\n".join(output)


# # Usage
def test():
    current_dir = Path(__file__).parent
    start_time = time.process_time()
    kb = DocGraph("/Users/unclecode/devs/crawl4ai/tmp/selected", "/Users/unclecode/devs/crawl4ai/docs/md_v2")
    kb.persist(f"{current_dir}/kb_v1.pkl")
    kb = DocGraph.load(f"{current_dir}/kb_v1.pkl")
    print(f"Indexing time: {time.process_time() - start_time:.2f} seconds")
    start_time = time.process_time()
    prompt = kb.query("LLm extraction implementation")
    end_time = time.process_time()
    print(f"Query time: {end_time - start_time:.2f} seconds")
    with open(f"{current_dir}/search_result_v1.md", "w") as f:
        f.write(prompt)

def test_repo():
    # Local paths
    # kb = DocGraph("/path/to/code", "/path/to/docs")

    # GitHub with specific paths
    kb = DocGraph(
        "https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        "https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2"
    )

    # GitHub with default docs path
    # kb = DocGraph("https://github.com/unclecode/crawl4ai/src/backend")
    context = kb.query("LLm extraction implementation")
    print(context)

def test_optimized_persistence():
    """Compare old and new persistence mechanisms"""
    current_dir = Path(__file__).parent
    cache_file = current_dir / "kb_v1.c4ai"
    
    print("Starting benchmark of optimized persistence...")
    print("-" * 50)
    
    # Step 1: Build knowledge graph
    print("Building knowledge graph from scratch...")
    start_time = time.process_time()
    kb = DocGraph(
        "https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        "https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2"
    )
    build_time = time.process_time() - start_time
    print(f"✓ Build time: {build_time:.2f} seconds")

    # Step 2: Save to disk with new format
    print("\nSaving to disk using optimized format...")
    start_time = time.process_time()
    kb.persist(cache_file)
    save_time = time.process_time() - start_time
    print(f"✓ Save time: {save_time:.2f} seconds")
    
    # Check file size
    file_size_mb = cache_file.stat().st_size / (1024 * 1024)
    print(f"✓ File size: {file_size_mb:.2f} MB")
    
    # Step 3: Load from disk with new format
    print("\nLoading from disk using optimized format...")
    start_time = time.process_time()
    kb_loaded = DocGraph.load(cache_file)
    load_time = time.process_time() - start_time
    print(f"✓ Load time: {load_time:.2f} seconds")
    print(f"✓ Load is {build_time/load_time:.1f}x faster than building")
    
    # Step 4: Verify functionality
    print("\nVerifying functionality with a test query...")
    start_time = time.process_time()
    query_result_kb = kb.query("crawling implementation steps")
    query_result_loaded = kb_loaded.query("crawling implementation steps")
    query_time = time.process_time() - start_time
    print(f"✓ Query time (kb): {query_time:.2f} seconds")
    print(f"✓ Query time (loaded): {query_time:.2f} seconds")
    
    print("\nSummary:")
    print(f"- Build time: {build_time:.2f}s")
    print(f"- Save time: {save_time:.2f}s")
    print(f"- Load time: {load_time:.2f}s")
    print(f"- File size: {file_size_mb:.2f}MB")
    print(f"- Query time: {query_time:.2f}s")
    print(f"- Speedup: {build_time/load_time:.1f}x")
    
    return kb_loaded

if __name__ == "__main__":
    test_optimized_persistence()