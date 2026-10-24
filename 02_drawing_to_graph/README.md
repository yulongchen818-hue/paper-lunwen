# 02_drawing_to_graph

Rule-based drawing-to-graph pipeline (no learned model, no OCR).

* `dwg_processor.py` converts native CAD files to DXF through an external converter (ODA File Converter)
  and drives per-sheet processing; set `dwg_base_path` and `dxf_output_path` to your own directories
  (the defaults are placeholders).
* `drawing_parser.py` traverses a DXF sheet entity by entity (`ezdxf`): counts line, circle, arc, polyline,
  dimension and text entities, recovers radius/centre/diameter from circles, classifies dimension strings
  by three regular expressions (radius, diameter, linear), collects text and multi-line text with insertion
  points, and records the model-space bounding box and layer table.
* `extract_dxf_understanding.py` is the low-level variant on the DXF tagger, tolerant of structurally
  imperfect DXF files produced by some converters; writes one JSON per sheet.
* `build_kg.py` builds the graph from JSON-LD data files through `graph_engine.py`, prints a self-check
  report and optionally exports JSON / Cypher / GraphML.

The segment-to-drawing mapping that `dwg_processor.py` reads from the project's drawing register has been
removed; supply your own. Scanned sheets pass through unprocessed by design.
