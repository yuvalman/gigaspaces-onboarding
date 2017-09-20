import requests

slack_headers = {'content-type': 'application/json'}

def _invite_user(token, email, headers):
    """
    Invite new user to slack team
    :param token: The token of the slack app that will invite the user
    :param email: The email of the user that will be invited
    :param headers: The headers for the http request for slack
    :return: invite the user
    """
    invite_user = requests.post(
        'https://slack.com/api/users.admin.invite?token={0}&email={1}'.format(
            token, email),
        headers=headers)
    return invite_user


def main(token, email):
    """
    Doing onboarding process for Slack user
    :param token: The token of the slack app that will invite the user
    :param email: The email of the user that will be invited
    :return:
    """
    invite_user = _invite_user(token, email, slack_headers)
    return invite_user
