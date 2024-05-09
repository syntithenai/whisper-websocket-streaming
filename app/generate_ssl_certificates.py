import os


# require apt-get install openssl and certbot
def generate_ssl_certificates():
    """generate ssl certficates for either localhost or specified domain name SSL_DOMAIN_NAME"""
    print('GEN CERTS')
    domain = os.environ.get('SSL_DOMAIN_NAME', 'localhost')
    email = os.environ.get('SSL_EMAIL', 'none@syntithenai.com')
    print(domain)
    cert_path = '/etc/letsencrypt/live/' + domain
    if domain == "localhost":
        print('GEN LOCALHOST SSL KEY')
        os.system(' '.join(['mkdir', '-p', cert_path]))
        cmd = [
            'openssl',
            'req',
            '-x509',
            '-newkey',
            'rsa:4096',
            '-keyout',
            cert_path +
            '/privkey.pem',
            '-out',
            cert_path +
            '/cert.pem',
            '-days',
            '365',
            '-nodes',
            '-subj',
            '/CN=localhost']
        os.system(' '.join(cmd))

    else:
        # files exist so renew
        if os.path.isfile(cert_path + '/cert.pem') and os.path.isfile(cert_path + \
        '/fullchain.pem') and os.path.isfile(cert_path + '/privkey.pem'):
            print('RENEW CERTS')
            cmd = ['certbot', '	renew']
            print(cmd)
            os.system(' '.join(cmd))

        else:
            print('GENERATE CERTS')
            cmd = [
                'certbot',
                'certonly',
                '-a',
                'standalone',
                '--agree-tos',
                '-d',
                domain,
                '-m',
                email,
                ' --noninteractive']
            print(cmd)
            os.system(' '.join(cmd))

if __name__ == "__main__":
	generate_ssl_certificates()
