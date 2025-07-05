flowchart TD
    A[Start NotifyBot] --> B[Parse CLI Arguments]
    B --> C{Check Required Files}
    C -->|Missing| D[Exit with Error]
    C -->|OK| E[Read Core Components]
    
    E --> F[Read from.txt]
    E --> G[Read subject.txt] 
    E --> H[Read body.html]
    E --> I[Read approver.txt]
    
    F --> J{Validate Core Components}
    G --> J
    H --> J
    I --> J
    
    J -->|Invalid| K[Exit with Error]
    J -->|Valid| L[Prepare Recipients]
    
    L --> M{to.txt exists?}
    M -->|No| N[Get Filtered Email IDs]
    M -->|Yes| O[Skip Filtering]
    
    N --> N1[Read inventory.csv]
    N1 --> N2[Read filter.txt]
    N2 --> N3[Apply Filter Conditions]
    N3 --> N4[Validate Emails]
    N4 --> N5[Write to to.txt]
    
    N5 --> P[Read additional_to.txt]
    O --> P
    P --> Q[Append Additional Emails]
    Q --> R[Deduplicate to.txt]
    
    R --> S{Dry Run Mode?}
    S -->|Yes| T[Send Draft to Approvers]
    T --> U[Log Dry Run Complete]
    U --> V[End]
    
    S -->|No| W[Read Final Recipients]
    W --> X[Read to.txt]
    W --> Y[Read cc.txt]
    W --> Z[Read bcc.txt]
    
    X --> AA[Prepare Attachments]
    Y --> AA
    Z --> AA
    
    AA --> BB{Recipients exist?}
    BB -->|No| CC[Exit - No Recipients]
    BB -->|Yes| DD[Process Batches]
    
    DD --> EE[Create Email Batch]
    EE --> FF[Create EmailMessage]
    FF --> GG[Set Headers]
    GG --> HH[Add HTML Body]
    HH --> II[Add Attachments]
    
    II --> JJ{Check Attachment Size}
    JJ -->|Too Large| KK[Skip Attachment]
    JJ -->|OK| LL[Attach File]
    
    KK --> MM[Send Email Batch]
    LL --> MM
    
    MM --> NN{Send Success?}
    NN -->|Yes| OO[Log Success]
    NN -->|No| PP[Log Error]
    
    OO --> QQ{More Batches?}
    PP --> QQ
    QQ -->|Yes| RR[Wait Delay]
    RR --> EE
    QQ -->|No| SS[Generate Summary]
    
    SS --> TT[Calculate Stats]
    TT --> UU[Log Final Summary]
    UU --> V
    
    style A fill:#e1f5fe
    style V fill:#c8e6c9
    style D fill:#ffcdd2
    style K fill:#ffcdd2
    style CC fill:#ffcdd2
    style T fill:#fff3e0
    style MM fill:#f3e5f5
    style SS fill:#e8f5e8
