# Section 4: Getting Started with AWS
## Preparation
### Set a unique suffix to use for the S3 bucket name:

--- 

# Activity 1 :

```
RANDOM_ID=$(aws secretsmanager get-random-password \
--exclude-punctuation --exclude-uppercase \
--password-length 6 --require-each-included-type \
--output text \
--query RandomPassword)

```

### Create S3 bucket:

`aws s3api create-bucket --bucket awsml-$RANDOM_ID`

Upload the file to AWS S3 Bucket
`aws s3 cp NLP.png s3://awsml-$RANDOM_ID `

Display Storage class
`aws s3api list-objects-v2 --bucket awsml-$RANDOM_ID `

Lifecycle Config
`aws s3api put-bucket-lifecycle-configuration \
    --bucket awsml-$RANDOM_ID \
    --lifecycle-configuration  file://lifecycle.json \
    `

## Clean up 
### Delete the file you copied to your S3 bucket:

`aws s3 rm s3://awsml-$RANDOM_ID/NLP.png`

### Delete the S3 bucket:

`aws s3api delete-bucket --bucket awsml-$RANDOM_ID `

