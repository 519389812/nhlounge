import base64
import os
import rsa
from CouponVerifier.settings import KEY_DIR


class RsaHandler:
    def __init__(self, key_version):
        self.public_key = None
        self.key_version = key_version
        self.public_key_path = os.path.join(KEY_DIR, 'public_key_' + self.key_version + '.pem')

    def is_key_exist(self):
        if os.path.exists(self.public_key_path):
            return True
        return False

    def load_keys(self):
        with open(self.public_key_path, 'rb') as f:
            self.public_key = rsa.PublicKey.load_pkcs1(f.read())

    def verify_text(self, text, signature_text):
        signature = base64.b64decode(signature_text.encode())
        try:
            rsa.verify(text.encode(), signature, self.public_key)
            return True
        except rsa.pkcs1.VerificationError:
            return False