Dear Application Team,

Please note that as of Red Hat OpenShift Container Platform 4.14, the DeploymentConfig API is officially deprecated. While still supported for now, DeploymentConfig is no longer recommended for new workloads.

As previously agreed, any DeploymentConfig objects that are inactive in DEV should be decommissioned 7 days after a successful migration to Deployment. However, we have observed that some DeploymentConfig instances in a stopped state remain in the cluster.

Please review the attached list for your {csiid} and proceed with the deletion of the listed DeploymentConfig objects as soon as possible—provided they are no longer in use and have been successfully migrated.

If you require assistance in verifying their status or need help with the migration process, feel free to reach out.

Thank you for your cooperation.
