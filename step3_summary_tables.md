# Step 3: Quick Reference Tables

## Missing in .env Files
### Variables Referenced in Code but Missing from Both .env and .env.example
```
┌─────────────────────┬──────────┬────────────┐
│ Variable Name       │ Type     │ Risk Level │
├─────────────────────┼──────────┼────────────┤
│ DB_PASSWORD         │ Database │ HIGH       │
│ NEO4J_DATABASE      │ Database │ MEDIUM     │
│ SUPABASE_DB_PASSWORD│ Database │ HIGH       │
│ VAR                 │ Generic  │ LOW        │
└─────────────────────┴──────────┴────────────┘
```

## Unused in Code
### Variables Present in .env but Never Referenced in Code
```
┌─────────────────────┬──────────────────────────────┬─────────────────────────────┐
│ Variable Name       │ Value                        │ Purpose                     │
├─────────────────────┼──────────────────────────────┼─────────────────────────────┤
│ ALLOWED_ORIGINS     │ http://localhost:3000,5173   │ CORS configuration          │
│ AURA_INSTANCEID     │ c74b6cb5                     │ Neo4j Aura config          │
│ AURA_INSTANCENAME   │ Instance01                   │ Neo4j Aura config          │
│ DEBUG               │ true                         │ Debug mode                  │
│ ENVIRONMENT         │ development                  │ Environment setting         │
│ JWT_SECRET_KEY      │ [MASKED]                     │ JWT authentication          │
│ LOG_FILE            │ ./logs/cinegraph.log         │ Logging configuration       │
│ LOG_LEVEL           │ INFO                         │ Logging level               │
│ MAX_FILE_SIZE       │ 10485760                     │ File upload limit           │
│ SECRET_KEY          │ [MASKED]                     │ Application secret          │
│ UPLOAD_FOLDER       │ ./uploads                    │ File upload directory       │
└─────────────────────┴──────────────────────────────┴─────────────────────────────┘
```

## Variable Name Mismatches
### Same Logical Variable, Different Names
```
┌─────────────────┬─────────────────┬──────────────────────────┬──────────────────────────────┐
│ Logical Variable│ .env Name       │ .env.example Name        │ Issue                        │
├─────────────────┼─────────────────┼──────────────────────────┼──────────────────────────────┤
│ Neo4j Password  │ NEO4J_PASSWORD  │ GRAPHITI_DATABASE_PASSWORD│ Inconsistent naming          │
│ Neo4j URI       │ NEO4J_URI       │ GRAPHITI_DATABASE_URL    │ Inconsistent naming          │
│ Neo4j Username  │ NEO4J_USERNAME  │ GRAPHITI_DATABASE_USER   │ Inconsistent naming          │
└─────────────────┴─────────────────┴──────────────────────────┴──────────────────────────────┘
```

## Summary Statistics
```
┌─────────────────────────────────────────────────────┬───────┐
│ Category                                            │ Count │
├─────────────────────────────────────────────────────┼───────┤
│ Variables in .env                                   │  29   │
│ Variables in .env.example                           │  17   │
│ Variables referenced in code                        │  22   │
│ Variables missing from both .env files              │   4   │
│ Variables in .env but not in .env.example           │  15   │
│ Variables unused in code (from .env)                │  11   │
│ Variables unused in code (from .env.example)        │   3   │
│ Potential naming mismatches                         │   3   │
│ Well-configured variables (in both files + code)    │  14   │
└─────────────────────────────────────────────────────┴───────┘
```

## Risk Assessment Summary
```
┌─────────────┬───────┬──────────────────────────────────────────────────────────────────────────────────────┐
│ Risk Level  │ Count │ Variables                                                                            │
├─────────────┼───────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ HIGH        │   6   │ DB_PASSWORD, DATABASE_URL, JWT_SECRET_KEY, SECRET_KEY, NEO4J_PASSWORD, NEO4J_URI,   │
│             │       │ SUPABASE_DB_PASSWORD                                                                 │
├─────────────┼───────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ MEDIUM      │   3   │ ALLOWED_ORIGINS, NEO4J_DATABASE, NEO4J_USERNAME                                     │
├─────────────┼───────┼──────────────────────────────────────────────────────────────────────────────────────┤
│ LOW         │  12   │ Configuration and optional variables                                                 │
└─────────────┴───────┴──────────────────────────────────────────────────────────────────────────────────────┘
```

## Key Findings
1. **4 variables** are referenced in code but missing from both .env files
2. **15 variables** are in .env but missing from .env.example (documentation gap)
3. **11 variables** in .env appear unused in code (potential cleanup candidates)
4. **3 naming mismatches** between NEO4J_* and GRAPHITI_DATABASE_* prefixes
5. **14 variables** are properly configured across all files
6. **6 high-risk variables** need immediate attention
