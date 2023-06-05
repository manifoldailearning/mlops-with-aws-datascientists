# Help for BuildSpec

https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html#build-spec-ref-example

# Appspec file

https://docs.aws.amazon.com/codedeploy/latest/userguide/reference-appspec-file-example.html

# Help for Metadata
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-categories.html

# AWS CLI Profile

**Create Profile**
aws configure --profile profile_name
*you need access key for cli*
~/.aws/credentials - contains stored creds
~/.aws/config - contains stored profile

*If Getting Error as Unable to commit*
- Goto Credential Manager in Windows & Remove the Existing credentials for codecommit
- Extra information - https://stackoverflow.com/questions/34517534/running-git-clone-against-aws-codecommits-gets-me-a-403-error





*Display Profile Names:*
aws configure list-profiles



