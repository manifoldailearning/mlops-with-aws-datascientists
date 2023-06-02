# Section 4: Getting Started with AWS
## Preparation
### Set a unique suffix to use for the S3 bucket name:

--- 

# Activity 2 : Create S3 Bucket using CLI

```
RANDOM_ID=$(aws secretsmanager get-random-password \
--exclude-punctuation --exclude-uppercase \
--password-length 6 --require-each-included-type \
--output text \
--query RandomPassword)

```

### Create S3 bucket:

``` aws s3api create-bucket --bucket awsml-$RANDOM_ID```

Upload the file to AWS S3 Bucket
```aws s3 cp NLP.png s3://awsml-$RANDOM_ID ```

Display Storage class
```aws s3api list-objects-v2 --bucket awsml-$RANDOM_ID ```

## Clean up 
### Delete the file you copied to your S3 bucket:

```aws s3 rm s3://awsml-$RANDOM_ID/NLP.png```

### Delete the S3 bucket:

```aws s3api delete-bucket --bucket awsml-$RANDOM_ID ```


---
# Activity 3 : Versioning hands On

- Follow the steps as above to create S3 bucket, and practice versioning
- Upload the same file (without versioning enabled) : It will overwrite
- Perform Version enablement & upload again
- delete the new version to get the previous version of file

---

