# gigaspaces-onboarding


This tool is used to fully automate GigaSpaces and Cloudify onboarding process.

It is using AWS services: Lambda, DynamoDB, SES.

API's used: AWS(boto3), OpenStack, Slack, Okta SSO, Samanage.

## How is it actually work? 

It is based in AWS Lambda, and run once a day using cron job.

First, it Add all the "Onboarding" incidents from Samanage to DynamoDB.

When the time is right, it creates users in Okta, RackSpace(OpenStack) and Slack:
- In Okta,it create automatically for the new worker users(depend on his department permissions) in all the needed 
apps (AWS, Microsoft Azure, GCP, Datadog, etc.) that support provisioning (using SAML).
- In RackSpace, it creates user and assign him to a personal project.
- In Slack, it invite new user to the right Slack team.

Last, it send Mail to the new worker and his manager with all the details (using SES).
