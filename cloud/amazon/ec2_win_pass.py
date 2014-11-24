#!/usr/bin/python

DOCUMENTATION = '''
---
module: ec2_win_pass
short_description: retrieve and decrypt password for an ec2 windows instance
description:
  - Retrieves and decrypts the Windows Administrator password for an EC2
    instance using the private key associated with the instance's key pair.
    The private key IS NOT transmitted to EC2, only used locally to decrypt
    the password.  This module has a dependency on python-boto and the openssl
    command line utility.
version_added: "1.8"
options:
  instance_id:
    description:
      - The EC2 instance id (e.g. i-XXXXXX)
    required: true
  private_key:
    description:
      - Content of private key
    required: true

author: Chris Church
extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Basic example of decrypting a password
tasks:
- name: get my ec2 windows password
  local_action: ec2_win_pass
    instance_id=i-123456
    private_key="{{ lookup('file', '~/.ssh/id_rsa') }}"
  register: my_pass
'''

import base64
import string
import sys
import tempfile

try:
    import boto.ec2
except ImportError:
    print "failed=True msg='boto required for this module'"
    sys.exit(1)

def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
            instance_id = dict(required=True),
            private_key = dict(required=True),
        )
    )
    module = AnsibleModule(argument_spec=argument_spec)

    instance_id = module.params.get('instance_id')
    private_key = module.params.get('private_key')

    ec2 = ec2_connect(module)
    password_data = ec2.get_password_data(instance_id)
    if not password_data:
        module.fail_json(msg='No encrypted password data found',
                         instance_id=instance_id)

    handle, pk_file  = tempfile.mkstemp()
    f = os.fdopen(handle, 'w')
    f.write(private_key)
    f.close()
    module.add_cleanup_file(pk_file)

    handle, pw_file  = tempfile.mkstemp()
    f = os.fdopen(handle, 'w')
    f.write(base64.decodestring(password_data))
    f.close()
    module.add_cleanup_file(pw_file)

    args = ['openssl', 'rsautl', '-in', pw_file, '-inkey', pk_file, '-decrypt']
    rc, stdout, stderr = module.run_command(args)
    if rc != 0:
        module.fail_json(msg='Error running openssl: %s' % stderr,
                         instance_id=instance_id)

    password = stdout.strip()
    valid_chars = set(string.digits + string.letters + string.punctuation)
    if not set(password) <= valid_chars:
        module.fail_json(msg='Unable to decrypt password data',
                         instance_id=instance_id)

    module.exit_json(changed=False, password=password,
                     instance_id=instance_id)
    sys.exit(0)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

main()
