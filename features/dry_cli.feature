@122 @dry
Feature: forge dry command and reporting
  Operators can run standalone DRY analysis and inspect structured output.

  Background:
    Given a forge project with default DRY configuration

  @cli
  Scenario: forge dry runs on source path
    When I run "forge dry --path src"
    Then the command exits with code 0
    And the output includes "DRY analysis"

  @json
  Scenario: JSON report includes similarity score
    Given "src/a.py" defines function "alpha" with body "return x + 1"
    And "src/b.py" defines function "beta" with body "return item + 1"
    When I run "forge dry --path src --json dry-report.json"
    Then the command exits with code 0
    And "dry-report.json" contains finding field "similarity_score"

  @console
  Scenario: Console report includes line range
    Given "src/a.py" defines function "alpha" with body "return x + 1"
    And "src/b.py" defines function "beta" with body "return item + 1"
    When I run "forge dry --path src"
    Then the output includes a line range for the finding

  @threshold
  Scenario Outline: Threshold filters candidate pairs
    Given two functions with structural similarity <threshold>
    When I run "forge dry --path src --threshold <threshold>"
    Then the DRY report has <finding_count> findings

    Examples:
      | threshold | finding_count |
      | 0.99      | 0             |
      | 0.82      | 1             |

  @filters
  Scenario: Small function excluded by min-nodes
    Given "src/tiny.py" defines a 2-line function "small" with body "return 1"
    When I run "forge dry --path src --min-nodes 20"
    Then the DRY report has 0 findings for "small"
