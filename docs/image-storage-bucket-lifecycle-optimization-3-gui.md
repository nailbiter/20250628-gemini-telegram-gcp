This is the same issue we've run into before—your `gcloud` command-line tool is outdated.

The `set-cleanup-policy` command is a newer feature, and your version of the SDK doesn't recognize it.

-----

### \#\# The Fix: Update Your `gcloud` SDK

The simplest solution is to update your `gcloud` tool to the latest version, which will include this command.

```bash
gcloud components update
```

After the update finishes, the `gcloud artifacts repositories set-cleanup-policy...` command should work.

-----

### \#\# Alternative: Use the GUI (One-Time Setup)

Since your local `gcloud` has been problematic, it might be faster to set this policy **one time** using the Google Cloud web console. This achieves the exact same result.

1.  Go to the **Artifact Registry** page in your Google Cloud Console.
2.  You will see a repository named `gcr.io`. Click on it.
3.  Click the **"Edit"** button at the top of the page.
4.  Scroll down to the **Cleanup Policies** section.
5.  Click **"Add Policy"**.
      * **Filter Type**: Select `Package prefix`.
      * **Package prefix**: Type `py-assistant-bot` (the name of your image).
      * **Keep Count**: Set the value to `10`.
6.  Click **"Done"** and then **"Save"**.

This will set the exact "keep 10 most recent versions" policy on your `py-assistant-bot` image, which will solve your storage cost problem without you needing to fight with your `gcloud` installation.