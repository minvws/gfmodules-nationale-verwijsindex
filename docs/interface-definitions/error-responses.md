# Error Responses

Errors are returned as FHIR OperationOutcome resources.

## Format

All error responses follow this structure:

- `resourceType` (string): Always `OperationOutcome`.
- `issue` (array): One or more issues describing the error.

Each `issue` entry includes:

- `severity` (string): The severity of the issue (e.g. `fatal`, `error`, `warning`, `information`).
- `code` (string): A code describing the type of error (FHIR IssueType code system).
- `details` (object, optional): Additional human-readable details.
  - `text` (string): A message describing the error.
- `expression` (array of string, optional): FHIRPath expressions identifying fields related to the error.

## Examples

```json
{
  "resourceType": "OperationOutcome",
  "issue": [
    {
      "severity": "error",
      "code": "invalid",
      "details": {
        "text": "NVIDataReference.source must be a valid `Identifier`"
      },
      "expression": [
        "NVIDataReference.source"
      ]
    }
  ]
}
```

```json
{
  "resourceType": "OperationOutcome",
  "issue": [
    {
      "severity": "error",
      "code": "forbidden",
      "details": {
        "text": "Organization is forbidden to access requested NVIDataReference"
      }
    }
  ]
}
```
