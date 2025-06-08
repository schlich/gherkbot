Feature: Basic Calculator Operations
  As a user
  I want to perform basic calculations
  So that I can get quick results

  Scenario: Adding two numbers
    Given I have entered 50 into the calculator
    And I have entered 70 into the calculator
    When I press add
    Then the result should be 120 on the screen

  Scenario: Subtracting two numbers
    Given I have entered 100 into the calculator
    And I have entered 30 into the calculator
    When I press subtract
    Then the result should be 70 on the screen
