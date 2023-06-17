
# Installing the CodeDeploy agent on EC2
** Updated way to install with SSM **
```YAML

- Create EC2 Instance with IAM Role attached
    - Assign the Policy `AmazonS3ReadOnlyAccess` to allow CodeDeploy agent to read the version from S3 Bucket
    - Add User Data as mentioned below
- Assign tags to EC2 Instances
- Launch the instance and run the command - `sudo service codedeploy-agent status` to validate - CodeDeploy Agent is not running in EC2 instance
- Create an Application in CodeDeploy
- Push app revision to S3 Bucket (create a S3 bucket with versioning if its not created) - see section - **deploy the files into S3** below
- Create a Service Role for CodeDeploy and assign Codedeploy policy
- Create CodeDeployment Group and assign IAM role created above
- Do necessary settings and create Code Deployment
- Now validate in EC2 after few seconds to see whether codeDeploy agent has been installed `sudo service codedeploy-agent status`
- Run the Deployment
- Verify whether the website is working (Make sure to check the security group of ec2 instance)
```
# User data
```
#!bin/bash
sudo yum update -y
sudo yum install -y ruby wget
wget https://aws-codedeploy-eu-west-1.s3.eu-west-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo service codedeploy-agent status
```
