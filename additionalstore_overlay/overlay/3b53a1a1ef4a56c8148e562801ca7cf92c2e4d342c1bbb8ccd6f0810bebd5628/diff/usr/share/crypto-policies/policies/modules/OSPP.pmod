# Restrict FIPS policy for the Common Criteria OSPP profile.

# Hashes: only SHA1, SHA2-256, SHA2-384, and SHA2-512
# MACs: HMAC with only SHA1, SHA2-256, SHA2-384, and SHA2-512
# Curves: only P-256, P-384, and P-521
# SSH ciphers: only aes128-ctr, aes256-ctr, aes128-cbc, and aes156-cbc
# SSH MACs: only hmac-sha1, hmac-sha1-96, hmac-sha2-256, hmac-sha2-512
# SSH key exchange: only diffie-hellman-group14-sha1, ecdh-sha2-nistp256,
#  ecdh-sha2-nistp384, ecdh-sha2-nistp521
# TLS protocols: TLS = 1.2, DTLS = 1.2

hash = -SHA2-224 -SHA3-256 -SHA3-384 -SHA3-512

ssh_group = -FFDHE-4096 -FFDHE-8192

cipher = -AES-256-CTR -AES-128-CTR

ssh_cipher = -AES-256-GCM -AES-256-CCM -AES-128-GCM -AES-128-CCM

ssh_certs = 0
ssh_etm = 0

protocol = -TLS1.3

arbitrary_dh_groups = 0
