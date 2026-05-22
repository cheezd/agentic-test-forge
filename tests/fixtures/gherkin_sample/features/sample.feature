Feature: Sample calculator

  Scenario Outline: Add numbers
    Given values <a> and <b>
    When they are added
    Then the result is <result>

    Examples:
      | a | b | result |
      | 1 | 2 | 3      |
      | 2 | 3 | 5      |

  Scenario: Plain scenario without examples
    Given nothing special
    When nothing happens
    Then nothing fails
