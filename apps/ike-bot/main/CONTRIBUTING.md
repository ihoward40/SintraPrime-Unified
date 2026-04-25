# Contributing to ike-bot Neo-Commonwealth Legal Strategy Automation

Thank you for your interest in contributing to the ike-bot project! This guide provides information on how to contribute effectively to the Neo-Commonwealth legal strategy automation system.

## Code Style Standards

### TypeScript Guidelines

1. **Type Safety**
   - Use strict TypeScript settings
   - Avoid `any` type whenever possible
   - Prefer explicit type annotations
   - Use interfaces for object shapes

2. **Naming Conventions**
   - Use PascalCase for classes and interfaces
   - Use camelCase for variables and functions
   - Use UPPER_SNAKE_CASE for constants
   - Use kebab-case for file names

3. **Code Organization**
   - Group related exports
   - Keep functions small and focused
   - Use descriptive names for functions and variables
   - Add JSDoc comments for all public functions

### Example Code Style

```typescript
// Interface definition
interface DocumentProcessingResult {
  afvStatus: AFVStatus;
  dischargeEligibility: DischargeEligibility;
  entities: ExtractedEntity[];
  compliance: ComplianceStatus;
}

// Class definition
export class DocumentProcessor {
  private readonly logger: Logger;
  private readonly parser: CommercialInstrumentParser;

  constructor(logger: Logger, parser: CommercialInstrumentParser) {
    this.logger = logger;
    this.parser = parser;
  }

  /**
   * Processes a document to extract legal information
   * @param content The document content to process
   * @param type The type of document
   * @returns Processing result with extracted information
   */
  public async processDocument(content: string, type: DocumentType): Promise<DocumentProcessingResult> {
    this.logger.debug(`Processing document of type: ${type}`);
    
    try {
      const result = await this.parser.parse(content, type);
      this.logger.debug(`Processing complete. Result: ${JSON.stringify(result)}`);
      return result;
    } catch (error) {
      this.logger.error(`Error processing document: ${error.message}`);
      throw new DocumentProcessingError(`Failed to process document: ${error.message}`);
    }
  }
}
```

## PR Review Checklist

### Before Submitting a PR

1. **Code Quality**
   - [ ] Code follows TypeScript style guidelines
   - [ ] No linting errors
   - [ ] All functions have JSDoc comments
   - [ ] No console.log statements (use logger instead)

2. **Testing**
   - [ ] All new code has unit tests
   - [ ] All tests pass
   - [ ] Code coverage is maintained or improved
   - [ ] Integration tests are included where appropriate

3. **Functionality**
   - [ ] Implementation matches issue requirements
   - [ ] Edge cases are handled
   - [ ] Error handling is appropriate
   - [ ] Performance considerations are addressed

### During Code Review

1. **Review Focus Areas**
   - Correctness of implementation
   - Adherence to architectural patterns
   - Security considerations
   - Performance implications

2. **Review Process**
   - Provide constructive feedback
   - Explain reasoning for suggested changes
   - Respond to reviewer comments promptly
   - Update PR based on feedback

## Testing Requirements

### Unit Tests

1. **Test Structure**
   - Use Jest as the testing framework
   - Organize tests in `__tests__` directories
   - Name test files with `.test.ts` suffix
   - Use descriptive test names

2. **Test Coverage**
   - Aim for at least 80% code coverage
   - Test all public functions
   - Test error conditions
   - Test edge cases

3. **Example Test Structure**

```typescript
import { AFVNotationDetector } from '../AFVNotationDetector';
import { AFVStatus } from '../types';

describe('AFVNotationDetector', () => {
  let detector: AFVNotationDetector;

  beforeEach(() => {
    detector = new AFVNotationDetector();
  });

  describe('detectAFVNotation', () => {
    it('should detect AFV notation in document', () => {
      const content = 'This document is Accepted for Value';
      const result = detector.detectAFVNotation(content);
      
      expect(result.present).toBe(true);
      expect(result.location).toBeDefined();
    });

    it('should not detect AFV notation when absent', () => {
      const content = 'This document has no AFV notation';
      const result = detector.detectAFVNotation(content);
      
      expect(result.present).toBe(false);
      expect(result.location).toBeUndefined();
    });

    it('should detect exemption notation', () => {
      const content = 'This document is Exempt from Levy';
      const result = detector.detectAFVNotation(content);
      
      expect(result.exempt).toBe(true);
    });
  });
});
```

### Integration Tests

1. **Test Scenarios**
   - Test module interactions
   - Test database operations
   - Test API integrations
   - Test end-to-end workflows

2. **Test Environment**
   - Use test database
   - Mock external APIs
   - Use test fixtures
   - Clean up after tests

## Branch and Commit Conventions

### Branch Naming

1. **Feature Branches**
   - Format: `feature/module-name`
   - Example: `feature/document-intelligence`
   - Example: `feature/compliance-checker`

2. **Bug Fix Branches**
   - Format: `fix/description-of-issue`
   - Example: `fix/afv-detection-accuracy`

3. **Release Branches**
   - Format: `release/version-number`
   - Example: `release/v1.2.0`

### Commit Messages

1. **Format**
   - Use conventional commits
   - Format: `type(scope): description`
   - Keep first line under 50 characters
   - Include body and footer when needed

2. **Types**
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `style`: Code style changes
   - `refactor`: Code refactoring
   - `test`: Test additions
   - `chore`: Build process or auxiliary tool changes

3. **Examples**

```
feat(document-intelligence): add AFV notation detection

Add pattern matching for AFV notation with 95% accuracy target.
Includes exemption detection and location tracking.

Closes #27

fix(compliance): correct CIA §7-101 rule validation

Fix incorrect exemption requirement checking that caused false
positives in compliance validation.

Closes #28
```

## Documentation Standards

### Code Documentation

1. **JSDoc Comments**
   - Document all public functions
   - Include parameter types
   - Include return types
   - Provide usage examples

2. **Example JSDoc**

```typescript
/**
 * Processes a document to extract legal information
 * @param content The document content to process
 * @param type The type of document
 * @returns Processing result with extracted information
 * @throws {DocumentProcessingError} When processing fails
 * @example
 * ```typescript
 * const result = await processor.processDocument(content, 'AFV');
 * console.log(result.afvStatus.present);
 * ```
 */
public async processDocument(content: string, type: DocumentType): Promise<DocumentProcessingResult>
```

### README Updates

1. **Module README**
   - Include in each module directory
   - Describe module purpose
   - Provide usage examples
   - Document configuration options

2. **Example Module README**

```markdown
# Document Intelligence Module

## Purpose
Process legal documents with focus on AFV notation detection and discharge eligibility assessment.

## Usage

```typescript
import { DocumentProcessor } from './DocumentProcessor';

const processor = new DocumentProcessor();
const result = await processor.processDocument(content, 'AFV');
```

## Configuration
- `DOCUMENT_INTELLIGENCE_DB_URL`: Supabase database URL
- `DOCUMENT_INTELLIGENCE_DB_KEY`: Supabase database key

## Testing
Run tests with `npm run test:document-intelligence`
```

## Development Workflow

### Setting Up Development Environment

1. **Prerequisites**
   - Node.js 16 or higher
   - npm or yarn
   - Git
   - VS Code (recommended)

2. **Setup Steps**
   ```bash
   # Clone repository
   git clone https://github.com/ihoward40/ike-bot.git
   cd ike-bot
   
   # Install dependencies
   npm install
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   
   # Run tests
   npm test
   ```

3. **Development Tools**
   - ESLint for code linting
   - Prettier for code formatting
   - Husky for git hooks
   - Jest for testing

### Making Changes

1. **Create Issue**
   - Describe the change needed
   - Include acceptance criteria
   - Assign appropriate labels

2. **Create Branch**
   ```bash
   git checkout -b feature/module-name
   ```

3. **Implement Changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

4. **Submit Changes**
   ```bash
   git add .
   git commit -m "feat(module): description of change"
   git push origin feature/module-name
   ```

5. **Create Pull Request**
   - Link to relevant issue
   - Include description of changes
   - Request review from maintainers

## Security Considerations

### Data Protection

1. **Sensitive Data**
   - Never commit API keys or secrets
   - Use environment variables for configuration
   - Implement proper access controls
   - Log security events

2. **Input Validation**
   - Validate all user inputs
   - Sanitize data before processing
   - Implement rate limiting
   - Handle errors gracefully

### Code Security

1. **Dependencies**
   - Regularly update dependencies
   - Use npm audit to check for vulnerabilities
   - Review third-party code before inclusion
   - Lock dependency versions

2. **Testing**
   - Include security tests
   - Test for common vulnerabilities
   - Perform code reviews with security focus
   - Use static analysis tools

## Performance Guidelines

### Code Optimization

1. **Efficient Algorithms**
   - Use appropriate data structures
   - Minimize computational complexity
   - Implement caching where appropriate
   - Optimize database queries

2. **Resource Management**
   - Release resources properly
   - Avoid memory leaks
   - Implement connection pooling
   - Monitor resource usage

### Monitoring

1. **Performance Metrics**
   - Track response times
   - Monitor resource usage
   - Log performance events
   - Set up alerts for anomalies

2. **Profiling**
   - Profile code regularly
   - Identify bottlenecks
   - Optimize critical paths
   - Validate improvements

## Getting Help

### Resources

1. **Documentation**
   - [Implementation Guide](./IMPLEMENTATION_GUIDE.md)
   - [API Reference](./API_REFERENCE.md)
   - [Architecture Overview](./ARCHITECTURE.md)

2. **Community**
   - GitHub Issues for questions
   - GitHub Discussions for ideas
   - Code reviews for feedback

### Contact

- Create an issue for questions
- Tag maintainers for urgent matters
- Use discussions for general questions

Thank you for contributing to ike-bot!