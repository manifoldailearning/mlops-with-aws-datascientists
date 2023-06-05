# Git commands

## Install Git
```
git --version
git config --global user.name "murthy"
git config --global user.email "support@manifoldailearning.in"
git config --global color.ui=true
git config --global -l
git config --global core.autocrlf true
```

If you’re programming on Windows and working with people who are not 
(or vice-versa), you’ll probably run into line-ending issues at some point. 
This is because Windows uses both a carriage-return character and a linefeed 
character for newlines in its files, whereas Mac and Linux systems use only
the linefeed character. This is a subtle but incredibly 
annoying fact of cross-platform work; many editors on Windows 
silently replace existing LF-style line endings with CRLF, or 
insert both line-ending characters when the user hits the enter key.

Git can handle this by auto-converting CRLF line endings into LF when you add a file to the index, and vice versa when it checks out code onto your filesystem. You can turn on this functionality with the core.autocrlf setting. If you’re on a Windows machine, set it to true – this converts LF endings into CRLF when you check out code:

## Create remote repositories in AWS code commit

```mkdir my-website # create folder
cd my-website
git init   #Start tracking
```

## Copy files to new folder
```
git status

git add .

git commit -m "This is my first commit"

git status

git log
```

## Other ways to add:
```
git add <list of files> --> adding list of files
git add --all -->Add all files
git add .  -->Add all files
git add *.txt --> Add all text files in current directory
git add docs/*.txt  --> Add all text files in docs directory
git add docs/  -->add all files in docs directory
```

## Staged differences
```
touch hello.txt
vi hello.txt - i to enter insert mode
write the text ands save

':wq' on keyboard  to save the file

git add .

git diff
```
Add some text again
```
git diff --staged
```

## Unstage

```
git reset HEAD hello.txt
git status
cat hello.txt
```
## Remove changes since last commit
```
git checkout -- hello.txt
git status
cat hello.txt

vi hello.txt # add some text for file
git add .
git commit hello.txt -m "this is a commit"
git status

git reset --soft HEAD^ # Reset to staging
git status

touch hello2.txt
git add hello2.txt
git commit --amend -m "New file has been added"


git reset --hard HEAD^ --> Undo last commit and all the changes
git reset --hard HEAD^^ --> Undo last two commits

git revert <commit id>
```
## Adding a Remote
```
git remote add origin https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/my-website


git remote -v # display remote repositories

git push -u origin master # push changes to remote repositories

```
##  goto commits in aws code commit

## create another remotes
git remote add dev2 <address>

##  remove remotes
git remote rm <name>

git push -u <name> <branch> # to push to remotes


# Section 3 - Cloning & Branching

## Clone a Repository
```
git clone <repo link>
git clone <repo link> <folder name>

git remote -v # points to clone URL
```

## Start working with Website
## Change title and push code to code commit


##  Branches 
```
git branch dev
git branch

git checkout dev

git checkout -b test

#modify on branch
git status

git checkout master
git status

git checkout dev
git add .
git commit -m "Fixed with youtube link"
git push -u origin dev

git checkout master
git merge dev # merge with branch
git push -u origin master

```
## Fast Forward


## remove branch
```
git branch -d dev --> remove a branch
git push -d origin dev
git branch -D dev --> Remove un merged branch

git branch

#Create new branch
git branch dev2
git checkout dev2
#edit on dev2 branch
git add .
git commit -m "change title"

#modify on master branch without pushing to remote repo
git checkout master
git branch
git pull # just pull the update from remote
#edit on Master branch
git add index.html
git commit -m "adjust case"
git push -u origin master


#switch back to branch of dev2
git branch
git checkout dev2
git status

#merge back to master
git checkout master
git merge dev2

#Conflict, Merge failed

git merge --abort
vi index.html
#perform fix on html file
git add index.html
git checkout index.html -m "fixed conflict"
git push -u origin master

#clear branch
git branch -d dev2
git push -d origin dev2

#create two branches
git branch qa
git branch dev
git branch
git checkout dev
#modify and commit & merge
git add .
git commit -m "update branch dev"
git push -u origin dev
git checkout master
git merge dev

#remove branches

git checkout qa
#do changes on qa branch
#merge with master
git pull origin master
#this will update branch qa

#Rebase --> Get the data status
git pull
git checkout -b dev
vi index.html # edit
git add .
git commit -m "changes on branch"
git checkout master
vi index.html #edit on a file
git add .
git commit -m " changes on master"
git checkout dev
git rebase master
vi index.html # fix issues
git log



#Other Commands
git diff HEAD^
git diff HEAD^^

```