from base_uploader import BaseUploader, run_uploader

class MoveUploader(BaseUploader):
    TYPENAME = "move"

    def handle(self, path, filename):
        self.send_message({"type": "fileup", "path": filename})
        return True

if __name__ == "__main__":
    run_uploader(MoveUploader)
