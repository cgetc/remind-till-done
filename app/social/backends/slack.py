from social_core.backends.slack import SlackOAuth2


class AddToSlackOAuth2(SlackOAuth2):
    STATE_PARAMETER = False

    def get_user_details(self, response):
        """Return user details from Slack team"""
        # Build the username with the team $username@$team_url
        # Necessary to get unique names for all of slack
        team = response['team']

        return {
            'username': team['name'],
            'email': '{domain}@{email_domain}'.format(**team),
            'fullname': team['domain'],
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        response = self.get_json('https://slack.com/api/team.info', params={'token': access_token})
        if not response.get('id', None):
            response['id'] = response['team']['id']

        return response
