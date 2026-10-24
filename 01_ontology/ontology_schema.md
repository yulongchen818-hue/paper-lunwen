# Ontology schema (lightweight semantic schema, JSON-LD)

The model declares 18 classes in four groups and 12 relation types (a 13th, `landsOn`, was added in graph
version 1.2). It is expressed in JSON-LD with the namespace prefix `sb:`. In formal terms it is a lightweight
semantic schema: it declares classes, properties and a property-to-edge mapping, but no OWL class axioms, no
domain and range restrictions and no SHACL shapes. Domain and range below are therefore declarations that
nothing enforces; `05_graph_audit/audit_graph.py` measures conformance after the fact.

## Classes

| Group | Class | What it represents |
|---|---|---|
| Project | Project | The structure being built |
| Project | GirderSegment | A segment of the box girder |
| Project | StructuralComponent | Arch ribs, braces, deck units, bearings and similar members |
| Project | ComponentSystem | A system grouping components (arch-rib system, girder system, substructure) |
| Process | ConstructionProcess | Fabrication and erection operations (cutting, fitting, welding, coating, testing) |
| Process | ConstructionMethod | The erection method (for example walking-jack incremental launching) |
| Process | PushRound | One launching stage; the entity that makes stage-dependent questions answerable |
| Process | Equipment | Jacks, cranes and other plant |
| Process | TemporaryStructure | Temporary piers, guide beam, assembly platform |
| Document | Drawing | One sheet of the drawing register, with the values recovered from it |
| Document | TechnicalSpecification | Governing codes and standards |
| Document | Quantity | Quantity take-off items |
| Context | Material | Steel grades, cables and other materials |
| Context | Stakeholder | Participating organizations |
| Context | SiteCondition | Site constraints |
| Context | Schedule | The programme |
| Context | KnowledgePoint | Curated engineering knowledge points |
| Context | Discipline | Discipline index for knowledge points |

## Relation types

| Relation | Declared domain -> range |
|---|---|
| partOfProject | Any -> Project |
| depicts | Drawing -> StructuralComponent |
| refersToDrawing | Any -> Drawing |
| usesMaterial | StructuralComponent -> Material |
| belongsTo | StructuralComponent -> ComponentSystem |
| usesMethod | Any -> ConstructionMethod / ConstructionProcess |
| appliesTo | TechnicalSpecification -> Any |
| involvesSegment | PushRound -> GirderSegment |
| hasComponent | ComponentSystem -> StructuralComponent |
| hasStep | ConstructionProcess -> ConstructionProcess |
| launchOrder | PushRound -> PushRound |
| relatedTo | Any -> Any (untyped fallback; counted as a data-quality indicator) |
| landsOn (v1.2) | launch step -> TemporaryStructure |

## Graph file format consumed by the code

`kg_graph.json` is a plain JSON object:

```json
{
  "nodes": [ { "id": "sb:Drawing_D0105", "type": "Drawing", "props": { "sb:name": "...", "sb:drawingNo": "D-01-05", "...": "..." } } ],
  "edges": [ { "source": "sb:Drawing_D0105", "target": "sb:Component_X", "label_en": "depicts", "provenance": "recorded" } ]
}
```

`props` holds the JSON-LD properties of the entity; a property value that is a string beginning with `sb:` is
treated as an entity reference, which is how `audit_graph.py` computes referential integrity. `provenance`
is `recorded` (stated in a document) or `derived` (inferred by a stated rule); edges without it predate the
repair changelog. The property-to-edge mapping that produces `edges` from `props` is in
`03_deterministic_retrieval/graph_engine.py`.
