from __future__ import annotations

import unittest

from govease_ai.chunking import build_chunks_for_store
from govease_ai.procedure_data import load_procedure_store


class ChunkingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = load_procedure_store()
        cls.chunks = build_chunks_for_store(cls.store)

    def test_store_loads_detailed_checkpoint_templates(self) -> None:
        codes = {record.code for record in self.store.detailed_records()}
        self.assertIn("1.001193", codes)
        self.assertIn("1.004194", codes)

    def test_chunks_include_citable_source_metadata(self) -> None:
        self.assertGreater(len(self.chunks), 20)
        citable = [chunk for chunk in self.chunks if chunk["metadata"].get("source_url")]
        self.assertGreater(len(citable), 20)
        self.assertTrue(all("procedure_code" in chunk["metadata"] for chunk in self.chunks))

    def test_chunks_are_logical_units(self) -> None:
        chunk_types = {chunk["metadata"]["content_type"] for chunk in self.chunks}
        self.assertIn("required_document", chunk_types)
        self.assertIn("step", chunk_types)
        self.assertIn("common_error", chunk_types)
        self.assertIn("validation_rule", chunk_types)


if __name__ == "__main__":
    unittest.main()
