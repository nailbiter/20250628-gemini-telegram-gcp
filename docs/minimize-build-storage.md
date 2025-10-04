Yes, you're absolutely right. That's a very important point to consider.

By default, every time you rebuild, Cloud Build creates a new image with a unique digest. The old, untagged images remain in storage and will accumulate over time, which could eventually push you over the free tier.

Fortunately, there's a simple, automated way to handle this.

-----

## \#\# The Solution: GCS Lifecycle Management

The best "set-it-and-forget-it" solution is to apply a **Lifecycle Management Policy** to the underlying Cloud Storage bucket where GCR stores your images. You can create a simple rule that automatically deletes old images.

Here’s how to set up a rule to delete any image that hasn't been used in **30 days**.

### \#\#\# 1. Create a Lifecycle Rule File

Create a file named `lifecycle.json` with the following content. This rule tells Cloud Storage to delete any object in the bucket that is older than 30 days.

```json
{
  "rule": [
    {
      "action": {
        "type": "Delete"
      },
      "condition": {
        "age": 30
      }
    }
  ]
}
```

### \#\#\# 2. Apply the Rule to Your GCR Bucket

GCR stores its images in a specific bucket named `artifacts.[YOUR_PROJECT_ID].appspot.com`. You can apply the rule to that bucket with a single `gcloud` command.

```bash
gcloud storage buckets update gs://artifacts.api-project-424250507607.appspot.com --lifecycle-file=lifecycle.json
```

That's it. Now, Google Cloud will automatically clean up old image layers for you in the background, ensuring your storage usage stays low and well within the free tier, no matter how often you rebuild.
