# Recipe-carried data contracts

A user recipe can define a structured retention contract without editing OpsFeast's product registry. The reviewed recipe produces its final domain data during execution. The platform validates and stores that data using the saved declaration; replay and import never execute a candidate normalizer.

```yaml
retention:
  contract: example-temperature
  version: '1.0.0'
  description: Temperature samples in degrees Celsius; null means unavailable.
  mode: portable
  data_schema:
    type: object
    additionalProperties: false
    required: [celsius]
    properties:
      celsius:
        type: [number, 'null']
        minimum: -273.15
```

This declaration is embedded in the data-only retention snapshot and retained envelope. Its saved snapshot digest binds the complete definition. A normalizer digest is unnecessary because no normalizer runs during retention/replay. The recipe's executed source tree and version remain recorded independently. Keep units, missing-value semantics, source timestamps and interpretation policy in the dataset/declaration; do not put presentation templates or executable code into it. Domain-specific consistency checks belong in the reviewed recipe's code before returning data. The platform's structural validator cannot infer business semantics from a type alone.

The public module `opsfeast.data_contract` provides `definition(schema)`, `validate(value, schema)`, canonical JSON, canonical UTC timestamp, canonical UUID validation and collection-evidence 0.1.0 validation. Controller Python 3.11+ and normal OpsFeast dependencies suffice. `definition` rejects unsupported keywords/references; `validate` raises ConfigError on invalid data. No new third-party schema dependency or network resolver is required.

The implemented dialect is **opsfeast-json-schema/0.1.0**, a documented subset of JSON Schema rather than a full Draft 2020-12 implementation. It supports object/array/string/number/integer/boolean/null types, properties/required/additionalProperties/propertyNames/dependentRequired, items and length/count/uniqueness bounds, enum/const, numeric bounds/multipleOf, allOf/anyOf/oneOf/not/if/then/else and local JSON-pointer `$ref` into `$defs`/definitions. Supported formats are date-time, date, uuid, uri and email; date-time requires a timezone. URI/email checks are structural, not connectivity or deliverability evidence. Title, description, examples, default, $id/$schema/$comment and the existing unit/property_catalog fields are annotations; defaults are not applied to data.

Portable schemas cannot fetch remote references or execute code. Package export bundles supported local external references into one offline document. Recursion and size limits are explicit; patterns are limited to 256 characters without backreferences/lookaround. Quantified-group expressions are evaluated in a bounded subprocess with a one-second timeout and at most 4096-character input; other pattern inputs are capped at 65536 characters. Rejected or timed-out rules fail rather than becoming successful validation. Unsupported dialect features require a product extension, not silent keyword omission.

The installed inventory, job, replication and older backup domain contracts still use their existing reviewed bundled normalizers for those producers. That registry does not gate new mode: portable contracts or imported saved datasets. Imported retention is validated against its carried definition and structural envelope, not against whichever recipe/normalizer happens to be installed today. Keep provenance and saved findings unchanged. See [independent transfer/import/archive](portability.md).


## Optional execution metadata and prerequisites

Saved envelopes preserve optional assessment and execution identity independently of portable business data. Authors may declare `portability.features` prerequisites for recipe-assessment, recipe-execution and portable-retention 0.1.0. See [the feature declaration and evidence guide](recipe-results-and-accounts.md#saved-evidence-and-portability).

*Last modified: 2026-10-26 11:49:24*
