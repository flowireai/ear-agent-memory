# Exfiltration demo (canary data only)

`v5_exfil_migration.html` is a poisoning page whose "new gateway" points to a local receiver the authors control
(`127.0.0.1:8899`). After the agent stored the poisoned endpoint in memory, a later routine task made it send a canary
API key and a dummy profile to that receiver. All credentials and personal data used were fake canary values.
This demo shows that a poisoned memory entry leads to real outbound behaviour; the paper's measurements focus on cleaning such entries.
