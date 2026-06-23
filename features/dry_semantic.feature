@122 @dry
Feature: Semantic DRY detection
  Forge reports structurally similar function bodies even when local names differ.

  Background:
    Given a forge project with DRY analysis enabled
    And the project contains Python source under "src"

  @semantic
  Scenario: Renamed locals reported as near-duplicate
    Given "src/a.py" defines function "alpha" with body "return x + 1"
    And "src/b.py" defines function "beta" with body "return item + 1"
    When I run "forge dry --path src"
    Then the DRY report contains a finding for "alpha" and "beta"
    And the finding similarity score is at least 0.82

  @exact
  Scenario: Identical bodies reported with score 1.00
    Given "src/a.py" defines function "foo" with body "return value * 2"
    And "src/b.py" defines function "bar" with body "return value * 2"
    When I run "forge dry --path src"
    Then the DRY report contains a finding for "foo" and "bar"
    And the finding similarity score is 1.00
