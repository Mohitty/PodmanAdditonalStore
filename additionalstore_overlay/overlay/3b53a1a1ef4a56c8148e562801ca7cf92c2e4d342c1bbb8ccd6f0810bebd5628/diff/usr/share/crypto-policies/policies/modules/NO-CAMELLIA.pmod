# This is example policy dropping the Camellia support altogether

tls_cipher = -CAMELLIA-256-GCM -CAMELLIA-256-CBC -CAMELLIA-128-GCM \
    -CAMELLIA-128-CBC

cipher = -CAMELLIA-256-GCM -CAMELLIA-256-CBC -CAMELLIA-128-GCM \
    -CAMELLIA-128-CBC
