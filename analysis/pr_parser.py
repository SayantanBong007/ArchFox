class PRParser:

    @staticmethod
    def extract_changed_files(pr_files):

        changed = []

        for file in pr_files:

            changed.append({
                "filename":file["filename"],
                "patch":file.get("patch", "")
            })

        return changed