All files here are authored synthetic rehearsal inputs, never ES operational data.
The semicolon path files deliberately use different field names, German local date
strings and midnight on the following calendar day. Only mappings/swap_paths.yaml
adapts them. Merged XLSX is authored from these rows at test/runtime; its original
headers are refused, then explicit flattening and a generated mapping permit intake.
The German notice is entered by a person with exact quotes (DD.MM.YYYY dates map to
ISO deterministically). Its recurrence is deliberately unknown. Admin data uses the
generic fallback. No external model, key, real railway event or download is needed.
