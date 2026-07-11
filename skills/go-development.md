# Go Development Skill

Best practices for Go development.

## Project Structure

```text
project/
├── cmd/            # Entry points
│   └── app/
│       └── main.go
├── internal/       # Private packages
│   ├── handler/
│   ├── service/
│   └── repository/
├── pkg/            # Public packages
├── api/            # API definitions
├── configs/        # Configuration files
└── scripts/        # Build scripts
```text

## Code Style

### Error Handling

```go
// Always handle errors explicitly
result, err := doSomething()
if err != nil {
    return fmt.Errorf("failed to do something: %w", err)
}

// Don't ignore errors
_ = doSomething() // Bad
```text

### Naming Conventions

```go
// Use short, clear names
func GetUser(id int) (*User, error) {}  // Good
func GetUserByID(id int) (*User, error) {}  // Also good

// Interfaces should describe behavior
type Reader interface {
    Read(p []byte) (n int, err error)
}
```text

### Testing

```go
// Table-driven tests
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", 
                    tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```text

## Best Practices

### goroutines

```go
// Use context for cancellation
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

go func() {
    select {
    case <-ctx.Done():
        return
    case result := <-ch:
        process(result)
    }
}()
```text

### Channels

```go
// Buffer channels when possible
ch := make(chan Result, 10)

// Close channels from sender side
defer close(ch)

// Use select for multiple channels
select {
case msg := <-ch1:
    handle(msg)
case <-ctx.Done():
    return
}
```text

### Defer

```go
// Defer for cleanup
func process() error {
    f, err := os.Open("file.txt")
    if err != nil {
        return err
    }
    defer f.Close()
    
    // Process file
    return nil
}
```text

## Common Patterns

### Repository Pattern

```go
type UserRepository interface {
    FindByID(id int) (*User, error)
    FindByEmail(email string) (*User, error)
    Save(user *User) error
}

type postgresUserRepository struct {
    db *sql.DB
}

func (r *postgresUserRepository) FindByID(id int) (*User, error) {
    // Implementation
}
```text

### Service Layer

```go
type UserService struct {
    repo   UserRepository
    logger *slog.Logger
}

func NewUserService(repo UserRepository, logger *slog.Logger) *UserService {
    return &UserService{repo: repo, logger: logger}
}

func (s *UserService) GetUser(id int) (*User, error) {
    user, err := s.repo.FindByID(id)
    if err != nil {
        s.logger.Error("failed to get user", "id", id, "error", err)
        return nil, err
    }
    return user, nil
}
```text

## Tools

### Essential

- `go fmt` — Format code
- `go vet` — Static analysis
- `golangci-lint` — Linter aggregator
- `go test` — Run tests
- `go mod tidy` — Clean dependencies

### Development

- `air` — Live reload
- `delve` — Debugger
- `pprof` — Profiling
