import logging
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# Set up logging
logging.basicConfig(filename='iosxe_verification.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class CiscoISR4331:
    def __init__(self, hostname, host, username, password, device_type='cisco_ios'):
        self.device = {
            
            'device_type': device_type,
            'host': host,
            'username': username,
            'password': password,
        }
        self.hostname = hostname
        self.connection = None
        self.iosbootfile = None

    def connect(self):
        """Establish SSH connection to the device."""
        try:
            self.connection = ConnectHandler(**self.device)
            logging.info(f"Successfully connected to {self.device['host']}")
        except NetmikoTimeoutException:
            logging.error(f"Timeout error connecting to {self.device['host']}")
            return False
        except NetmikoAuthenticationException:
            logging.error(f"Authentication error connecting to {self.device['host']}")
            return False
        except Exception as e:
            logging.error(f"Error connecting to {self.device['host']}: {str(e)}")
            return False
        return True

    def disconnect(self):
        """Disconnect from the device."""
        if self.connection:
            self.connection.disconnect()
            logging.info(f"Disconnected from {self.device['host']}")

    def find_latest_iosxe_file(self):
        """Find the IOS-XE image with the highest version number on bootflash."""
        try:
            output = self.connection.send_command("dir bootflash:")
            logging.debug(f"Bootflash directory output: {output}")

            ios_files = []
            for line in output.splitlines():
                if ".bin" in line:
                    filename = line.split()[-1]
                    ios_files.append(filename)

            if ios_files:
                # Sort IOS files based on version numbers
                ios_files.sort(reverse=True)
                self.iosbootfile = ios_files[0]
                logging.info(f"Latest IOS-XE image found: {self.iosbootfile}")
                return True
            else:
                logging.error("No IOS-XE .bin files found in bootflash.")
                return False
        except Exception as e:
            logging.error(f"Error finding latest IOS-XE file: {str(e)}")
            return False

    def validate_boot_statement(self):
        """Validate that the boot statement matches the detected iosbootfile."""
        try:
            if not self.iosbootfile:
                logging.error("No latest IOS-XE image found to validate boot statement.")
                return False

            output = self.connection.send_command("show run | include boot system")
            logging.debug(f"Boot statement output: {output}")

            expected_boot = f"boot system flash bootflash:{self.iosbootfile}"
            if expected_boot in output:
                logging.info(f"Boot statement matches the latest IOS-XE image: {self.iosbootfile}")
                return True
            else:
                logging.error(f"Boot statement does not match the latest image: {self.iosbootfile}")
                return False
        except Exception as e:
            logging.error(f"Error validating boot statement: {str(e)}")
            return False

    def verify_ios_image_signature(self):
        """Verify the integrity of the iosbootfile using the 'verify' command."""
        try:
            if not self.iosbootfile:
                logging.error("No latest IOS-XE image found to verify.")
                return False

            output = self.connection.send_command(f"verify bootflash:{self.iosbootfile}",read_timeout=1000)
            logging.debug(f"Verification output for {self.iosbootfile}: {output}")

            if "signature successfully" in output.lower():
                logging.info(f"Image {self.iosbootfile} verification successful.")
                return True
            else:
                error_msg = f"Error: Signature verification failed for {self.iosbootfile}."
                logging.error(error_msg)
                print(error_msg)
                return False
        except Exception as e:
            logging.error(f"Error during image verification: {str(e)}")
            return False

    def run_validation(self):
        """Run the full validation process: finding the latest image, validating the boot statement, and verifying the signature."""
        if self.connect():
            latest_file_found = self.find_latest_iosxe_file()
            if latest_file_found:
                boot_valid = self.validate_boot_statement()
                if boot_valid:
                    signature_valid = self.verify_ios_image_signature()
                    self.disconnect()

                    if signature_valid:
                        logging.info(f"Validation complete: All checks passed successfully on {self.hostname}.")
                        return True
                    else:
                        logging.error(f"Validation failed: Signature verification failed on {self.hostname}.")
                        return False
                else:
                    logging.error(f"Validation failed: Boot statement does not match on {self.hostname}")
                    self.disconnect()
                    return False
            else:
                logging.error(f"Validation failed: No valid IOS-XE image found on {self.hostname}.")
                self.disconnect()
                return False
        else:
            logging.error(f"Connection to device failed, cannot run validation on {self.hostname}.")
            return False

# Example Usage
if __name__ == "__main__":
    router = CiscoISR4331(
        hostname = 'howdy',
        host='127.0.0.1',         # Replace with your router's IP
        username='MyUser',        # Replace with your username
        password='MyPass'   # Replace with your password
    )
    router.run_validation()