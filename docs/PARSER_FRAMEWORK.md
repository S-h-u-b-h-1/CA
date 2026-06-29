# Parser Framework & Registry

The Parser Framework registers and resolves parsers for different document types.

## Base Class

All parsers inherit from `BaseParser`:
```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        """Parses extracted document text and returns structured facts"""
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        """Returns the supported category name"""
        pass
```

## Registry Auto-Resolution

Parsers are registered using `ParserRegistry.register(category, parser_class)`. When a document is processed:
1. `DocumentPipelineOrchestrator.classify_document` runs layout and filename regex checks.
2. The orchestrator queries `ParserRegistry.get_parser(category)`.
3. If no exact category match is found, it performs a soft-match on substrings before falling back to `GeneralDocumentParser`.
