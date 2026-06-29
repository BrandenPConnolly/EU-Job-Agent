from .keyword import KeywordScorer
from .llm import LLMScorer


def build_scorer(config, force_keyword: bool = False):
    """Return (scorer, mode_string). Falls back to keyword if Ollama unreachable."""
    if not force_keyword and config.use_llm:
        scorer = LLMScorer(config)
        if scorer.healthy():
            return scorer, f"llm ({config.ollama_model})"
        print(f"  ! Ollama not reachable at {config.ollama_host} or model '{config.ollama_model}' not loaded — using keyword scorer")
    return KeywordScorer(config), "keyword"
