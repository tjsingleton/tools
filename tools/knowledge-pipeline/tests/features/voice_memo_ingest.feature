Feature: Voice memo ingestion

  Scenario: Discover audio files
    Given a directory with .m4a and .qta files
    When I run discover
    Then all audio files are found
    And each file has a SHA-256 content hash

  Scenario: Idempotent ingest
    Given a previously ingested voice memo
    When I run ingest again
    Then no duplicate events are written
