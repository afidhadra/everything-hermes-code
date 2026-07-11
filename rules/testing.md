# Testing Rules

## Test-Driven Development

- Write tests before implementation
- One test case per assertion (when possible)
- Test behavior, not implementation
- Keep tests fast (<1 second)

## Test Types

- **Unit**: Test individual functions/methods
- **Integration**: Test component interactions
- **E2E**: Test complete user flows

## Test Coverage

- Aim for 80%+ coverage on business logic
- Focus on critical paths
- Don't chase 100% coverage
- Cover edge cases and error paths

## Test Quality

- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- Mock external dependencies
- Clean up after tests

## Test Organization

- One test file per source file
- Group related tests
- Use describe/it blocks
- Keep test files under 200 lines
