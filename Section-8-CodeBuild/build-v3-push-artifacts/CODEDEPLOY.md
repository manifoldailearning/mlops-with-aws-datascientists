
# Installing the CodeDeploy agent on EC2
# https://docs.aws.amazon.com/codedeploy/latest/userguide/codedeploy-agent-operations-install-ubuntu.html
```
sudo yum update -y
sudo yum install ruby
sudo yum install wget
cd /home/ec2-user
wget https://aws-codedeploy-ap-south-1.s3.ap-south-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo service codedeploy-agent status

#If error
sudo service codedeploy-agent start
sudo service codedeploy-agent status
```


# create a bucket and enable versioning
# https://docs.aws.amazon.com/cli/latest/reference/s3/mb.html
# https://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-versioning.html
```
aws s3 mb s3://aws-devops-manifold --region ap-south-1 --profile murthy
aws s3api put-bucket-versioning --bucket aws-devops-manifold --versioning-configuration Status=Enabled --region ap-south-1 --profile murthy
```

# deploy the files into S3
# https://docs.aws.amazon.com/cli/latest/reference/deploy/push.html
```
aws deploy push --application-name MyDeployDemo --s3-location s3://aws-devops-manifold/MyDeployDemo-test/app.zip --ignore-hidden-files --region ap-south-1 --profile murthy
```