import os
from keystoneauth1.identity import v3
from keystoneauth1 import session
import keystoneclient.v3
from novaclient import client
# import yaml
import random

# def _config_file(path_to_file):
#     with open(path_to_file) as config:
#         config_files = yaml.load(config.read())
#         return config_files
#
# conf_file = _config_file(
#     '/home/yuvalm-pcu/Documents/scripts/onboarding-config.yaml')

rackspace_user_domain_name = os.getenv('rackspace_user_domain_name')
rackspace_admin_username = os.getenv('rackspace_admin_username')
rackspace_admin_password = os.getenv('rackspace_admin_password')
rackspace_project_domain_name = os.getenv('rackspace_project_domain_name')
rackspace_project_name = os.getenv('rackspace_project_name')
rackspace_auth_url = os.getenv('rackspace_auth_url')
rackspace_project_domain_name = os.getenv('rackspace_project_domain_name')


def _openstack_auth(rackspace_user_domain_name, username, password,
                    rackspace_project_domain_name,
                    rackspace_project_name, rackspace_auth_url):
    """
    Authenticating with Openstack
    :param rackspace_user_domain_name: The domain name of the user
    :param username: The username of the user(Should be admin user)
    :param password: The password of the admin user
    :param rackspace_project_domain_name: The domain name of the project
    :param rackspace_project_name: The project name that the user
    will be added to
    :param rackspace_auth_url: The auth url of the Rackspace account
    :return: The authentication
    """
    auth = v3.Password(user_domain_name=rackspace_user_domain_name,
                       username=username,
                       password=password,
                       project_domain_name=\
                           rackspace_project_domain_name,
                       project_name=rackspace_project_name,
                       auth_url=rackspace_auth_url)
    return auth


def _openstack_client_session(client, *args):
    """
    Open session with Openstack client
    :param client: The Openstack client
    :param args: The arguments that should be added to open a session.
    For example - 'version'
    :return: The Openstack client
    """
    auth = _openstack_auth(rackspace_user_domain_name,
                           rackspace_admin_username,
                           rackspace_admin_password,
                           rackspace_project_domain_name,
                           rackspace_project_name,
                           rackspace_auth_url)
    sess = session.Session(auth=auth)
    openstack_client = client(*args, session=sess)
    return openstack_client


def _generate_password(pass_len):
    """
    Generate random password
    :param pass_len: The password length
    :return: The random password
    """
    all_keyboard_letters = "abcdefghijklmnopqrstuvwxyz" \
                           "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()?"
    random_password = "".join(random.sample(all_keyboard_letters,pass_len))
    return random_password


def _create_user(client, username):
    """
    Create user in Rackspace
    :param client: The Openstack client
    :param username: The username that will be created in Rackspace
    :return: The User that was created
    """
    random_password = _generate_password(8)
    user = client.users.create(username, password=random_password)
    return {'user': user, 'random_password': random_password}


def _create_project(client, rackspace_project_domain_name, username):
    """
    Create project in Rackspace
    :param client: The Openstack client
    :param rackspace_project_domain_name: The domain name of the project
    :param username:The username of the user
    :return: The project that was created
    """
    rackspace_project_name = '{0}-tenant'.format(username)
    project = client.projects.create(rackspace_project_name,
                                     rackspace_project_domain_name)
    return project


def _get_role_id(client, role_name):
    """
    Get role id of the role name parameter
    :param client: The Openstack client
    :param role_name: The name of the role
    :return: Role id
    """
    roles = client.roles.list()
    for role in roles:
        if role.name == role_name:
            return role.id


def _add_user_to_project(client, role_name, user_id, project_id):
    """
    Add user to a project
    :param client: The Openstack client
    :param role_name: The role that will be granted to the user
    :param user_id: The ID of the user that will be added to a project
    :param project_id: The ID of the project that the user will be added to
    :return: Grant the role to the user in the project
    """
    role_id = _get_role_id(client, role_name)
    grant_role = client.roles.grant(role_id, user=user_id, project=project_id)
    return grant_role


def _add_monitoring_user_to_project(client, project_id):
    """
    Add monitoring user to a project
    :param client: The Openstack client
    :param project_id: The ID of the project that the monitoring user
    will be added to
    :return: Grant admin role to the monitoring user in the project
    """
    users_list = client.users.list()
    for user in users_list:
        if user.name == 'monitoring':
            monitoring_user_id = user.id
            grant_admin_role = _add_user_to_project(client,
                                                    'admin',
                                                    monitoring_user_id,
                                                    project_id)
            return grant_admin_role


def _update_project_quotas(client, project_id, **kwargs):
    """
    Update the project quotas
    :param client: The Openstack client
    :param project_id: The ID of the project
    :param kwargs: Modify the quotas of the project
    :return: The project with updated quotas
    """
    project_quotas_update = client.quotas.update(project_id, **kwargs)
    return project_quotas_update


def main(username):
    """
    Doing onboarding process for Rackspace user
    :param username: The username of the user that will be created
    :return: The user that will be created
    """
    keystone_client = _openstack_client_session(keystoneclient.v3.client.Client)
    project = _create_project(keystone_client,
                              rackspace_project_domain_name,
                              username)
    user = _create_user(keystone_client, username)
    _add_user_to_project(keystone_client, '_member_', user['user'].id,
                         project.id)
    _add_monitoring_user_to_project(keystone_client, project.id)
    nova_client = _openstack_client_session(client.Client, 2)
    _update_project_quotas(nova_client, project.id,
                           cores=10,
                           fixed_ips=-1,
                           floating_ips=2,
                           injected_file_content_bytes=10240,
                           injected_file_path_bytes=255,
                           injected_files=5, instances=5,
                           key_pairs=4, metadata_items=128,
                           ram=44000, security_group_rules=20,
                           security_groups=10,
                           server_group_members=10,
                           server_groups=10)
    return user

