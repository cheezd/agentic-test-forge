@122 @dry @advisory
Feature: DRY gate is advisory
  DRY findings inform refactoring but never fail quality gates.

  Background:
    Given a forge project with gates.dry enabled in configuration
    And the project contains duplicate function bodies

  Scenario: forge check exits success with DRY findings
    When I run "forge check --path src"
    Then the command exits with code 0
    And the output includes DRY findings

  Scenario: forge dry exits success with DRY findings
    When I run "forge dry --path src"
    Then the command exits with code 0
    And the output includes at least 1 DRY finding
