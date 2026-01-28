#!/usr/bin/env python3
"""
Decode base64-encoded credentials from environment variables
Run this before starting the Flask app on Railway
"""
import os
import base64

def decode_file_from_env(env_var_name, output_filename):
    """Decode base64 environment variable to file"""
    encoded_content = os.environ.get(env_var_name)

    if not encoded_content:
        print(f"Warning: {env_var_name} environment variable not set")
        return False

    try:
        decoded_content = base64.b64decode(encoded_content)
        with open(output_filename, 'wb') as f:
            f.write(decoded_content)
        print(f"✓ Created {output_filename} from {env_var_name}")
        return True
    except Exception as e:
        print(f"Error decoding {env_var_name}: {e}")
        return False

if __name__ == "__main__":
    print("Decoding credentials from environment variables...")

    # Decode service account (preferred for server deployments)
    if decode_file_from_env('GOOGLE_SERVICE_ACCOUNT_BASE64', 'service-account.json'):
        print("Service account configured - will use service account authentication")
    else:
        # Fall back to OAuth credentials
        print("No service account found - falling back to OAuth")
        decode_file_from_env('GOOGLE_CREDENTIALS_BASE64', 'credentials.json')
        decode_file_from_env('GOOGLE_TOKEN_BASE64', 'token.pickle')

    print("Done!")
