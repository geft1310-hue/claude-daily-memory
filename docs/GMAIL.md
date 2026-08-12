# Gmail access and cleanup

Claude Daily Memory does **not** copy email into daily memory. Gmail access is a separate interactive connector.

Recommended permissions:

- read messages and labels;
- compose and send when the user gives an unambiguous task;
- apply labels and move matching messages to Trash;
- do not permanently delete messages and do not empty Trash.

## Cleanup without repeated confirmations

A cleanup rule is durable authorization to move exact matches to Trash. Every positive condition in the rule must match. Exclusions win. If a field is missing or ambiguous, the message stays in the inbox.

Safe rule fields:

- sender address or sender domain;
- subject regular expression;
- required Gmail labels;
- minimum message age;
- excluded senders and excluded subject patterns.

The connector should report only totals by rule after a batch. Message bodies are not included in that report or in daily memory.

See [`gmail-cleanup.example.yml`](gmail-cleanup.example.yml).
