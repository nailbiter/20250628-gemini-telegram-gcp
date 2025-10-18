Yes, you've spotted an important distinction, which highlights a misunderstanding in my previous advice. My apologies. Let's correct this, because your observation is key to getting the policy right.

You are 100% correct about the `..._cloudbuild` bucket. Here's the breakdown:

1.  **`..._cloudbuild` (Your Bucket):** This bucket is used by **Cloud Build** to store your *source code* (the `.zip` or `.tgz` file) and logs. This is generally small.

2.  **`gcr.io` (Artifact Registry):** This is where your *final container images* are stored. Your bill correctly shows this as **"Artifact Registry"** because Google now hosts all new `gcr.io` repositories on the modern Artifact Registry platform. This 3.067 GiB of image storage is your main cost.

-----

### The Critical Correction

My previous advice to use a GCS lifecycle policy (with `isLive=false`) was **incorrect**. That policy only works for the *older* GCR service.

Your bill confirms you are on the new Artifact Registry platform, which **does not use GCS lifecycle policies**. Instead, it uses its own "Cleanup Policies."

As you rightly feared, Artifact Registry's policies do not have an `isLive` condition. This means a simple age-based policy (e.g., "delete after 60 days") is **dangerous** and could break your running services if you don't redeploy them.

-----

### The Safe Solution: Cleanup by Version Count

The safest and simplest way to manage your Artifact Registry storage is to **limit the number of image versions** you keep, rather than deleting by age.

A policy that says "delete any image except for the 10 most recent versions" will:

  * Keep your storage costs very low (you'll only ever store 10 versions of your image).
  * Be **safe**, because it will never delete an image that is actively in use (unless you try to roll back to a very old, deleted version).

You can apply this policy to your `gcr.io` repository with the following `gcloud` command.

```bash
gcloud artifacts repositories set-cleanup-policy gcr.io \
  --project=$GCLOUD_PROJECT \
  --policy-file=cleanup-policy.json
```

**Contents of `cleanup-policy.json`:**
Create this new file. This policy keeps the 10 most recent versions and deletes all others.

```json
{
  "action": {
    "type": "Delete"
  },
  "condition": {
    "versionAgeDays": 0,
    "packageNamePrefixes": [
      "py-assistant-bot"
    ],
    "keepCount": 10
  }
}
```

This is the correct, safe, and modern way to manage your storage costs for Artifact Registry.