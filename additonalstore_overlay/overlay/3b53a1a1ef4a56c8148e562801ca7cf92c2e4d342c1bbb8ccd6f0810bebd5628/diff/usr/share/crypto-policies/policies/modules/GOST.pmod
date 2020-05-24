# This is example policy, the algorithm names might differ in reality
# Add GOST algorithms.

# This adds the HMAC-GOST at the end of the mac list
mac = HMAC-GOST+

# This adds the GOST-EC to the beginning of the group list
group = +GOST-EC

hash = +GOSTHASH

sign = +GOST-EC-GOSTHASH

tls_cipher = +GOST-CIPHER

cipher = +GOST-CIPHER

key_exchange = +GOST-EC
