import codecs
import re
import sys


class Commit:
    def __init__(self, commit, message):
        self.commit = commit
        self.message = message
        self.files = []


class LogExtract:
    """Summarise changes per file and files per change for a git repository

    The input file should be generated with the command:
        git log --name-status --format=%s --oneline ^low_rev high_rev
    """

    def __init__(self, filename):
        self.file = codecs.open(filename, encoding='utf-16')
        self.commit_pattern = re.compile(u'^[0-9a-f]{7} ', re.UNICODE)
        self.files = {}
        self.changes = 0
        self.commits = []
        self.exclude_paths = ['test/']
        self.filter_text = ['fixed', 'fixes', 'fix']

    def process(self):
        for line in self.file:
            line = line.rstrip()

            if self.is_commit_message(line):
                self.commits.append(Commit(line[:7], line[7:]))
                self.changes += 1
            elif line[0:1] != 'D':  # ignore deletions
                fname = line[2:]
                if self.should_process_file(fname):
                    self.update_file_commits(fname)

    def update_file_commits(self, fname):
        self.commits[-1].files.append(fname)

        if fname not in self.files:
            self.files[fname] = set()

        self.files[fname].add(self.commits[-1].commit)

    def is_commit_message(self, logmsg):
        return self.commit_pattern.match(logmsg) is not None

    def should_process_file(self, filename):
        # ignore non-python files and files outside the main folder.
        if not filename.endswith(".py") or not filename.startswith('django/'):
            return False

        # ignore any specifically excluded paths
        for path in self.exclude_paths:
            if filename.startswith('django/' + path):
                return False

        return True

    def message_filter(self, msg):
        for txt in self.filter_text:
            if msg.lower().find(' %s ' % txt) > -1:
                return True

        return False

    def summary(self):
        # remove commits with no files
        self.commits = filter((lambda c: len(c.files) > 0), self.commits)
        # remove commits not 'fixes'
        self.commits = filter((lambda c: self.message_filter(c.message)), self.commits)
        # sort commits by number of files descending
        self.commits = sorted(self.commits, key=lambda c: len(c.files), reverse=True)

        # create set of unique commit hashes
        unique_commits = set()
        for commits in self.commits:
            unique_commits.add(commits.commit)

        # remove any commits not in the resultant list from the file commit lists
        for k, v in self.files.items():
            self.files[k] = unique_commits.intersection(v)

        print "%d changes, %d files" % (len(self.commits), len(self.files))

        # how many files in the first 80% of changes?
        eighty_pc = int(len(self.commits) * 0.8)
        unique_files = set()
        for commits in self.commits[0:eighty_pc]:
            unique_files.update(commits.files)
        file_pc = (len(unique_files) * 100.00) / len(self.files)
        print "80%% of the changes (%d) were in %2.2f%% of the files (%d)" % (eighty_pc, file_pc, len(unique_files))

        # how many changes in the first 20% of files?
        twenty_pc = int(len(self.files) * 0.2)
        unique_commits = set()
        for commits in sorted(self.files.values(), key=lambda fs: len(fs), reverse=True)[0:twenty_pc]:
            unique_commits.update(commits)
        file_pc = (len(unique_commits) * 100.00) / len(self.commits)
        print "20%% of the files (%d) had %2.2f%% of the changes (%d)" % (twenty_pc, file_pc, len(unique_commits))


def main(logfile):
    extract = LogExtract(logfile)
    extract.process()
    extract.summary()


if __name__ == "__main__":
    main(sys.argv[1])

