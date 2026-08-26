# Ships the analyst notebook to the instance.
#
# There is no AWS API that writes a file into a notebook instance's EBS volume,
# so the only declarative options are a git clone (see var.notebook_git_repo) or
# staging the file in S3 and pulling it down from the lifecycle script. This is
# the latter: it ships whatever is in the working tree, with no push required.

resource "aws_s3_bucket" "assets" {
  bucket = "${var.project}-assets-${data.aws_caller_identity.current.account_id}"

  # The bucket holds one generated artifact and nothing of record, so let
  # `terraform destroy` remove it without a manual empty-the-bucket step.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "notebook" {
  bucket = aws_s3_bucket.assets.id
  key    = "notebook/phishbowl_triage.ipynb"
  source = "${path.module}/../notebook/phishbowl_triage.ipynb"

  # Re-uploads when the local notebook changes.
  etag         = filemd5("${path.module}/../notebook/phishbowl_triage.ipynb")
  content_type = "application/x-ipynb+json"
}
