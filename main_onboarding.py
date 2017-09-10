import json
import logging
import os
from datetime import datetime

import boto3
import rackspace_onboarding
import requests
import yaml
from jinja2 import Template


def _config_var(config_file_path):
    with open(config_file_path) as config:
        conf_var = yaml.load(config.read())
        return conf_var


# def _s3_object_read(client,bucket,key):
#     client = boto3.client(client)
#     object = client.get_object(
#         Bucket=bucket,
#         Key=key
#     )
#     return object['Body'].read()


def _request_get_elements(element, headers):
    """
    GET http request in Json format
   :param element: The request url
   :param headers: The headers for the request
   :return: http request in json format
   """
    request_for_get_element = requests.get(element, headers=headers)
    return request_for_get_element.json()

log_format =\
    '[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
logging.basicConfig(
    format=log_format, datefmt='%m-%d %H:%M:%S', level=logging.INFO)
logger = logging.getLogger(__name__)

conf_vars = _config_var(
    '/home/yuvalm-pcu/Documents/scripts/onboarding-config.yaml')
okta_api_access_token = conf_vars['okta_api_access_token']
# s3_object = yaml.load(_s3_object_read('s3', 'yuvalm', 'okta-aws-config.yaml'))
request_samanage_incidents =\
    'https://api.samanage.com/incidents.json?layout=long'
samanage_token = conf_vars['samanage_token']
samanage_headers = {'X-Samanage-Authorization': 'Bearer {0}'.format(
    samanage_token),
                    'Accept': 'application/vnd.samanage.v2.1+json',
                    'Content-Type': 'application/json'}
okta_headers = {'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': 'SSWS {0}'.format(okta_api_access_token)}
samanage_incidents = _request_get_elements(request_samanage_incidents,
                                           samanage_headers)
parms_list = ['Start date', 'First Name', 'Last Name',
              'Company mail', 'Private mail', 'Cost Center',
              'Mobile # (example:+972123456789)', 'Title', 'Employee Type',
              'Work Address', 'Manager']

okta_user_data_dict = {}
source = conf_vars['source']
forticlient_windows_download = conf_vars['forticlient_windows_download']
forticlient_mac_download = conf_vars['forticlient_mac_download']
forticlient_linux_download = conf_vars['forticlient_linux_download']
forticlient_remote_gateway = conf_vars['forticlient_remote_gateway']
forticlient_port = conf_vars['forticlient_port']
rackspace_url = conf_vars['rackspace_url']


# samanage_token = os.getenv('samanage_token')
# okta_api_access_token = os.getenv('okta_api_access_token')
# okta_api_org = os.getenv('okta_api_org')
# source = os.getenv('source')
# forticlient_windows_download = os.getenv('forticlient_windows_download')
# forticlient_mac_download = os.getenv('forticlient_mac_download')
# forticlient_linux_download = os.getenv('forticlient_linux_download')
# forticlient_remote_gateway = os.getenv('forticlient_remote_gateway')
# forticlient_port = os.getenv('forticlient_port')
# rackspace_url = os.getenv('rackspace_url')

def _request_create_element(element, headers, data):
    """
    POST http request in Json format
   :param element: The request url
   :param headers: The headers for the request
   :param data: The data that will be created with the request
   :return: http request in json format
   """
    request_for_create_element = requests.post(element, headers=headers,
                                               data=data)
    return request_for_create_element.json()


def _request_update_element(element, headers, data):
    """
    PUT http request in Json format
   :param element: The request url
   :param headers: The headers for the request
   :param data: The data that will be updated with the request
   :return: http request in json format
   """
    request_for_update_element = requests.put(element, headers=headers,
                                              data=data)
    return request_for_update_element.json()


def _ret_diff_val_from_the_same_dict(dict_name, value1,
                                     key1='name', key2='value'):
    """
    Check what is the value of key1 and return value of key2
   :param dict_name:  Dictionary with 3 keys(type, name, value)
   :param value1: value of key1
   :param key1: This key will always be 'name'
   :param key2: This key will always be 'value'
   :return: value of the key 'value'
   """
    if dict_name[key1] == value1:
        return dict_name[key2]


def _ret_manager_item_from_dict(manager_vars_dict, item):
    """
    Take the value of the group id of the 'Manager' var (from the samanage
    onboarding request), and use this value to get the details of the manager
    :param manager_vars_dict: Dictionary with 3 keys(type, name, value) that
    related to the manager of the new user
    :param item: This is var that is part of parameter from list of parameters
    of the new user
    :return: The details of the manager of the new user
    """
    manager_group_id = _ret_diff_val_from_the_same_dict(manager_vars_dict, item)
    manager_group = 'https://api.samanage.com/groups/{0}.json'.format(
        manager_group_id)
    manager_user = _request_get_elements(manager_group, samanage_headers)
    return manager_user


def _create_current_user_dict(vars_list, parameters):
    """
    Create current user data from the items that are in list of parameters
    of the new user
    :param vars_list: list of dictionaries from samanage onboarding request
    :param parameters: list of parameters of the new user
    :return: dict of user data + manager mail
    """
    current_user = {}
    for dictionary in vars_list:
        for parameter in dictionary.iteritems():
            for item in parameters:
                if item in parameter:
                    if item == 'Manager':
                        manager_user = _ret_manager_item_from_dict(
                            dictionary, item)
                        current_user[item] = manager_user['name']
                        manager_mail = manager_user['email']
                    else:
                        user_value = _ret_diff_val_from_the_same_dict(
                            dictionary, item)
                        current_user[item] = user_value
    return {'current_user': current_user, 'manager_mail': manager_mail}


def _get_okta_group_id(group_name):
    """
    GET Okta group ID
    :param group_name: The name of the Okta group
    :return: Okta group ID
    """
    get_okta_group = 'https://gigaspaces.okta.com/api/v1/groups?q={0}'.format(
        group_name)
    okta_group = _request_get_elements(get_okta_group, okta_headers)
    okta_group_id = okta_group[0]['id']
    return okta_group_id



def _build_okta_user_profile_from_samange_incident(incident, current_user_dict):
    """
    Build the profile of the Okta user
    :param incident: The onboarding samanage request
    :param current_user_dict: The dict of the user data
    :return: Okta user profile + user department
    """
    user_state = incident['site']['name']
    department_okta_group_name = incident['department']['name']
    department = department_okta_group_name.split(', ', 1)[1]
    okta_group_id = _get_okta_group_id(department_okta_group_name)
    okta_user_profile = {
        'profile': {
            'firstName': current_user_dict['First Name'],
            'state': user_state,
            'lastName': current_user_dict['Last Name'],
            'email': current_user_dict['Company mail'],
            'login': current_user_dict['Company mail'],
            'secondEmail': current_user_dict['Private mail'],
            'mobilePhone': current_user_dict['Mobile '
                                             '# (example:+972123456789)'],
            'costCenter': current_user_dict['Cost Center'],
            'title': current_user_dict['Title'],
            'department': department,
            'manager': current_user_dict['Manager'],
            'userType': current_user_dict['Employee Type'],
            'address': current_user_dict['Work Address']
        },
        'groupIds': [
            okta_group_id

        ]
    }
    okta_user_profile = json.dumps(okta_user_profile)
    return {'okta_user_profile': okta_user_profile,
            'user_department': department_okta_group_name}


def _rackspace_onboarding(okta_user, manager_mail):
    """
    Doing Onboarding process from rackspace_onboarding file
    :param okta_user: The details of the Okta user
    :param manager_mail: The email of the manager of the user
    :return: Rackspace user
    """
    user_name_prefix = okta_user['profile']['email'].split('@')[0]
    rackspace_user = rackspace_onboarding.main(user_name_prefix)
    rackspace_username = rackspace_user['user'].name
    rackspace_password = rackspace_user['random_password']
    _send_ses_mail('ses', 'us-east-1', source,
                   'rackspace_mail_template',
                   user_first_name=okta_user['profile']['firstName'],
                   company_mail=okta_user['profile']['email'],
                   manager_mail=manager_mail,
                   rackspace_url=rackspace_url,
                   rackspace_username=rackspace_username,
                   rackspace_password=rackspace_password,
                   forticlient_windows_download=forticlient_windows_download,
                   forticlient_mac_download=forticlient_mac_download,
                   forticlient_linux_download=forticlient_linux_download,
                   forticlient_remote_gateway=forticlient_remote_gateway,
                   forticlient_port=forticlient_port)
    return rackspace_user

def _create_okta_user(data):
    """
    Create Okta user with http requset without activate the user
    :param data: The data that will be created with the request
    :return: The Okta user
    """
    activate_okta_user =\
        'https://gigaspaces.okta.com/api/v1/users?activate=false'
    create_okta_user = _request_create_element(
        activate_okta_user, okta_headers, data)
    return create_okta_user


def _request_for_activate_okta_user(element, headers):
    """
    HTTP request for getting activation link for Okta in json format
    :param element: The request url
    :param headers: The headers for the request
    :return: request for activate okta user in json format
    """
    request_for_create_element = requests.post(element, headers=headers)
    return request_for_create_element.json()


def _get_activation_link(user_id):
    """
    Get activation link for user in Okta
    :param user_id: The ID of the new user
    :return: Activation link for the user
    """
    activate_user =\
        'https://gigaspaces.okta.com/api/v1/users/{0}/' \
        'lifecycle/activate?sendEmail=false'.format(user_id)
    activation_link = _request_for_activate_okta_user(
        activate_user, okta_headers)
    activation_url = activation_link['activationUrl']
    return activation_url


def _put_incident_in_dynamodb(client, incident,
                              dynamodb_table='OnBoarding_Incidents'):
    """
    Put the incident id and his details in dynamodb only if the incident id is
    not there yet
    :param client: AWS client
    :param incident: The onboarding request from samanage
    :param dynamodb_table: The table that the incident will be upload to
    :return: Put incident item in dynamodb table, True if incident already in DB
    """
    try:
        dynamodb = boto3.resource(client, region_name='us-east-1')
        table = dynamodb.Table(dynamodb_table)
        incident_id = incident['id']
        return table.put_item(Item={'incident_id': incident_id,
                                    'incident_info': json.dumps(incident)},
                              ConditionExpression='attribute_not_exists'
                                                  '(incident_id)')
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        logger.info('The incident id: {0} is already in the table: {1}'.format(
            incident_id, dynamodb_table))
        return True


def _creating_user_time(current_user_dict):
    """
    Check when is the time for creating the user
    :param current_user_dict: The dict of the user data
    :return:
    """
    today = datetime.now().date()
    start_date = datetime.strptime(
        current_user_dict['Start date'], "%Y-%m-%d").date()
    days = (start_date - today).days
    if days < 8:
        return True


def _open_directory_file(file_name):
    """
    Open the file name with read permission
    :param file_name: The name of the file in the same directory of the script
    :return:
    """
    dir_path = os.path.dirname(__file__)
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'r') as f:
        data = f.read()
    return data


def _create_mail_message(file_name, **kwargs):
    """
    Create mail message from a template
    :param file_name: The name of the file in the same directory of the script
    :param kwargs: Key Arguments that will be added to the mail
    :return: The message that will be sent as an email
    """
    mail_template = Template(_open_directory_file(file_name))
    message = mail_template.render(**kwargs)
    return message


def _send_ses_mail(client, region, source, file_name, **kwargs):
    """
    Sending mail in html format via SES client in AWS
    :param client: AWS client
    :param region: AWS region
    :param source: The mail address that the message will be sent from
    :param file_name: The name of the file in the same directory of the script
    :param kwargs: Key Arguments that will be added to the mail
    :return: sending raw mail via ses client
    """

    ses_client = boto3.client(client, region_name=region)
    message = _create_mail_message(file_name, **kwargs)
    send_mail = ses_client.send_raw_email(Source=source,
                                          RawMessage={'Data': message})
    return send_mail



# def _cloudify_onboarding():
#     pass
#
#
# def _imc_on_boarding():
#     pass


def main():
    """
    Doing Onboarding process for new employees in Gigaspaces and Cloudify
    companies
    """
    for incident in samanage_incidents:
        if incident['name'] == 'Employee - On Boarding'\
                and incident['assignee']['email'] == 'yuvalm@gigaspaces.com':
            custom_vars = incident['request_variables']
            user_dict = _create_current_user_dict(
                custom_vars, parms_list)
            current_user = user_dict['current_user']
            time_to_create_user = _creating_user_time(current_user)
            if time_to_create_user is True:
                item_in_dynamodb = _put_incident_in_dynamodb(
                    'dynamodb', incident)
                if item_in_dynamodb is True:
                    pass
                else:
                    user_profile =\
                        _build_okta_user_profile_from_samange_incident(
                            incident, current_user)
                    okta_user = _create_okta_user(
                        user_profile['okta_user_profile'])
                    okta_user_id = okta_user['id']
                    manager_mail = user_dict['manager_mail']
                    # if okta_user['profile']['costCenter'] == 'Cloudify':
                    #     _cloudify_onboarding()
                    # if okta_user['profile']['costCenter'] == 'IMC':
                    #     _imc_on_boarding()
                    if user_profile['user_department'] == 'Cloudify, R&D':
                        _rackspace_onboarding(okta_user, manager_mail)
                    activation_link = _get_activation_link(okta_user_id)
                    _send_ses_mail('ses', 'us-east-1', source,
                                   'onboarding_mail_template',
                                   company_name=okta_user['profile']['costCenter'],
                                   user_first_name=okta_user['profile']['firstName'],
                                   private_mail=okta_user['profile']['secondEmail'],
                                   company_mail=okta_user['profile']['email'],
                                   manager_mail=manager_mail,
                                   activation_link=activation_link,
                                   forticlient_windows_download=forticlient_windows_download,
                                   forticlient_mac_download=forticlient_mac_download,
                                   forticlient_linux_download=forticlient_linux_download,
                                   forticlient_remote_gateway=forticlient_remote_gateway,
                                   forticlient_port=forticlient_port)


if __name__ == '__main__':
    main()
