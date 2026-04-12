Feature: Voice memo analysis

  Scenario: Budget defers analysis when halt approached
    Given a document and a budget router at halt threshold
    When I run analyze
    Then a BudgetDeferred event is written
    And no AnalysisCompleted event is written
