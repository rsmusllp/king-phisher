# Contributing
The intent of this document is to outline the steps for a user to get started
with making contributions to the main King Phisher repository or one of it's
subproject repositories.

## Making Changes
The following steps are used to propose changes to the repository in the form
of a pull request.

  * Clone the repository
  * Create a topic branch that is up to date with the `dev` branch
  * Make your changes to this branch
    * Ensure all unit tests pass after the changes are implemented
  * Push the topic branch up to your repository on GitHub
  * Submit a Pull Request to the `dev` branch
    * Explain what the changes do (why they are useful, what they fix etc.)
    * Include steps to test the changes
  * Work with the repository owners by answering questions and making changes
  * Wait for the pull request to be merged
  * Enjoy a tasty beverage, you earned it!

Some things that will increase the chance that your pull request is accepted
and generally speed things along:

* Write documentation for functions that are not event or signal handlers
* Write unit tests
* Follow our [style guide][style]
* Write a [good commit message][commit]

[style]: http://king-phisher.readthedocs.io/en/latest/development/style_guide.html
[commit]: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
