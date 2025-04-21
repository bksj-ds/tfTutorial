# -*- coding: utf-8 -*-
"""
Created on Sun Apr 20 17:23:32 2025

@author: TF
"""
import sys
import os
import ccxt
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox

import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
#-------------------------------
#
# API 매니저 통합 클래스
#
#-------------------------------
class APIManager:
    def __init__(self, parent, exchange_name="bybit", testnet=False, file_path = "api_keys.txt"):
        self.parent = parent  # Reference to the main UI window
        self.exchange_name = exchange_name
        self.testnet = testnet
        self.exchange = None
        self.api_key = None
        self.secret_key = None
        self.api_password = None  # Needed for Bitget
        self.file_path = file_path or f"{exchange_name}_api_keys.enc"
        self._initialize_encryption()
        
    def _initialize_encryption(self):
        """Initialize encryption key and Fernet instance"""
        # Create a directory for storing keys if it doesn't exist
        os.makedirs('.keys', exist_ok=True)
        
        # Path for the encryption key
        key_path = os.path.join('.keys', '.master.key')
        
        # Generate or load master key
        if os.path.exists(key_path):
            with open(key_path, 'rb') as key_file:
                self.master_key = key_file.read()
        else:
            # Generate a random salt
            self.salt = os.urandom(16)
            
            # Use PBKDF2 to derive a key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            
            # Generate a random master key
            self.master_key = base64.urlsafe_b64encode(os.urandom(32))
            
            # Save the master key
            with open(key_path, 'wb') as key_file:
                key_file.write(self.master_key)
            
            # Save the salt
            with open(os.path.join('.keys', '.salt'), 'wb') as salt_file:
                salt_file.write(self.salt)
        
        # Initialize Fernet for encryption/decryption
        self.fernet = Fernet(self.master_key)
        
    #########################
    #
    # API 연동 화면 대응
    #
    #########################
    def load_api_key_if_exists(self, parent):
        """Load encrypted keys from the file if it exists and is readable."""
        try:
            api_key, secret_key, password = self.decrypt_api_keys()
            if api_key and secret_key:
                parent.apiKeyEdit.setPlainText(api_key)
                parent.secretKeyEdit.setPlainText(secret_key)
                if hasattr(parent, 'pwEdit') and password:
                    parent.pwEdit.setPlainText(password)
        except Exception as e:
            QMessageBox.warning(None, "오류", f"API 키 파일을 읽는 중 오류 발생: {e}")
        
    def save_keys(self, parent):
        """Save API keys with encryption."""
        # Retrieve input values
        api_key = parent.apiKeyEdit.toPlainText().strip()
        secret_key = parent.secretKeyEdit.toPlainText().strip()
        password = parent.pwEdit.toPlainText().strip() if hasattr(parent, 'pwEdit') else None

        if api_key and secret_key:
            try:
                # Save API keys with encryption (including password if provided)
                success = self.encrypt_api_keys(api_key, secret_key, password)
                
                if success:
                    QMessageBox.information(self.parent, "성공", "API 키 등록 성공")
                    parent.close()
                else:
                    QMessageBox.warning(self.parent, "오류", "API 키 암호화 실패")
            except Exception as e:
                QMessageBox.warning(self.parent, "오류", f"API 키 저장 중 오류 발생: {e}")
        else:
            QMessageBox.warning(self.parent, "오류", "API 키와 Secret 키 모두 등록 필요")
    
    #########################
    #
    # API 키 불러오기
    #
    #########################
    def load_api_key(self):
        """Load encrypted API keys."""
        try:
            # Try to load encrypted keys
            self.api_key, self.secret_key, self.api_password = self.decrypt_api_keys()
            
            # If encryption load fails, try legacy format
            if not self.api_key or not self.secret_key:
                if os.path.exists(self.file_path.replace('.enc', '.txt')) and os.access(self.file_path.replace('.enc', '.txt'), os.R_OK):
                    with open(self.file_path.replace('.enc', '.txt'), "r") as file:
                        lines = file.readlines()
                        keys = {line.split("=")[0]: line.split("=")[1].strip() for line in lines if "=" in line}
                        self.api_key = keys.get("API_KEY", "")
                        self.secret_key = keys.get("SECRET_KEY", "")
                        self.api_password = keys.get("API_PASSWORD", "")
            
            return bool(self.api_key and self.secret_key)
            
        except Exception as e:
            if hasattr(self.parent, 'log_message'):
                self.parent.log_message(f"API 키 로드 실패: {e}")
            return False
            
    def get_api_keys(self):
        """Retrieve API keys securely."""
        if not self.load_api_key():
            QMessageBox.warning(self.parent, "오류", "API 키 파일을 찾을 수 없거나 읽을 수 없습니다.")
            return False

        if not self.api_key or not self.secret_key:
            QMessageBox.warning(self.parent, "오류", "API 키와 Secret 키를 등록하세요.")
            return False

        if (self.exchange_name == "bitget" or self.exchange_name == "okx") and not self.api_password:
            QMessageBox.warning(self.parent, "오류", "API 비밀번호가 필요합니다.")
            return False

        return True
            
    def initialize_exchange(self):
        """Initialize API connection with the selected exchange."""
        if not self.get_api_keys():
            return
        
        try:
            exchange_class = getattr(ccxt, self.exchange_name)

            exchange_params = {
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                'adjustForTimeDifference': True,
                'verbose': True,
                'defaultType': 'future'
                },
            }
            if self.exchange_name in ['gateio']:
                exchange_params.get('options').update({'defaultType': 'swap'})  # Bitget requires password
                
            if self.exchange_name in ['bitget', 'okx']:
                exchange_params['password'] = self.api_password  # Bitget requires password

            self.exchange = exchange_class(exchange_params)

            if self.testnet:
                self.exchange.set_sandbox_mode(True)
                
            return self.exchange

        except Exception as e:
            
            return print(f'{e}')

    def encrypt_api_keys(self, api_key, secret_key, password=None):
        """Encrypt API keys using Fernet symmetric encryption"""
        try:
            # Convert keys to JSON string with password for Bitget/OKX
            keys_dict = {
                "api_key": api_key,
                "secret_key": secret_key,
                "exchange": self.exchange_name,
                "testnet": self.testnet
            }
            
            # Add password for Bitget/OKX
            if password and self.exchange_name in ['bitget', 'okx']:
                keys_dict["api_password"] = password
            
            keys_json = json.dumps(keys_dict)
            
            # Encrypt the JSON string
            encrypted_data = self.fernet.encrypt(keys_json.encode())
            
            # Save encrypted data to file
            with open(self.file_path, 'wb') as f:
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            if hasattr(self.parent, 'log_message'):
                self.parent.log_message(f"❌ API 키 암호화 실패: {str(e)}")
            return False
    
    def decrypt_api_keys(self):
        """Decrypt API keys from encrypted file"""
        try:
            if not os.path.exists(self.file_path):
                return None, None, None
            
            # Read encrypted data
            with open(self.file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt the data
            decrypted_json = self.fernet.decrypt(encrypted_data)
            keys_dict = json.loads(decrypted_json.decode())
            
            # Return API key, secret key, and password (if exists)
            return (
                keys_dict.get("api_key"),
                keys_dict.get("secret_key"),
                keys_dict.get("api_password")  # Will be None if not present
            )
        except Exception as e:
            if hasattr(self.parent, 'log_message'):
                self.parent.log_message(f"❌ API 키 복호화 실패: {str(e)}")
            return None, None, None
    
    def save_api_keys(self, api_key, secret_key):
        """Save API keys securely with encryption"""
        return self.encrypt_api_keys(api_key, secret_key)
    
    def load_api_keys(self):
        """Load and decrypt saved API keys"""
        return self.decrypt_api_keys()
    
class ApiKeyDialog(QDialog):
    def __init__(self, api_manager: APIManager, ui_path: str):
        super().__init__()
        self.api_manager = api_manager

        # Load the UI
        uic.loadUi(ui_path, self)

        # Connect the save button to logic
        self.saveButton.clicked.connect(self.save_api_keys)

    def save_api_keys(self):
        api_key = self.apiKeyEdit.toPlainText().strip()
        secret_key = self.secretKeyEdit.toPlainText().strip()
        password = self.passwordEdit.toPlainText().strip()

        if not api_key or not secret_key:
            QMessageBox.warning(self, "입력 오류", "API Key와 Secret Key를 모두 입력해주세요.")
            return

        try:
            result = self.api_manager.encrypt_api_keys(api_key, secret_key, password)
            if result:
                QMessageBox.information(self, "성공", "API 키 저장 완료")
                self.close()
            else:
                QMessageBox.warning(self, "실패", "API 키 저장에 실패했습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"API 키 저장 중 오류 발생: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    api_manager = APIManager(None, exchange_name="bybit")

    dialog = ApiKeyDialog(api_manager, "register_auth.ui")  # XML에서 만든 UI 경로
    
    dialog.show()

    sys.exit(app.exec_())