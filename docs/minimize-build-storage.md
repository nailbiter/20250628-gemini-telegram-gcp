# old
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

# better

That's an excellent and critical question. You've identified the exact weakness of that simple lifecycle rule. You are correct.

If you deploy a service and don't touch it for 31 days, the simple `age: 30` rule **would delete the image**, and your service would break the next time it tried to start a new instance (e.g., scaling up from zero).

The good news is that Cloud Storage has a much smarter condition specifically for this scenario.

-----

## \#\# The Better Solution: The `isLive` Condition

We can create a more intelligent rule that says: "Delete images that are older than 60 days, **but only if they are not actively being used by a Cloud Run service.**"

This is done with the `isLive` condition. An image is considered "live" if it's referenced by any active Cloud Run revision. This prevents you from deleting an image that a deployed service depends on.

### \#\#\# 1. Create a Safer `lifecycle.json`

Here is a more robust lifecycle rule. It combines three conditions to give you a safe and cost-effective policy:

```json
{
  "rule": [
    {
      "action": {
        "type": "Delete"
      },
      "condition": {
        "isLive": false,
        "age": 60,
        "numNewerVersions": 5
      }
    }
  ]
}
```

This single rule translates to: "Delete an image only if **ALL** of these are true:

  * It is **not** currently used by an active Cloud Run service (`"isLive": false`).
  * It is older than 60 days (`"age": 60`).
  * There are at least 5 newer versions of the image already in the registry (`"numNewerVersions": 5`).

This gives you multiple layers of protection. It will never delete a running service's image, it keeps old images for a reasonable time, and it always preserves your 5 most recent builds.

### \#\#\# 2. Apply the New Rule

You can apply this safer rule with the same command as before:

```bash
gcloud storage buckets update gs://artifacts.api-project-424250507607.appspot.com --lifecycle-file=lifecycle.json
```

This is the recommended approach for production systems, as it automates cleanup without risking your running services.
