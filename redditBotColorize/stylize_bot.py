import traceback
import argparse
import image_downloader
import image_uploader
import secret_keys
import praw
import time
import re
import database

parser = argparse.ArgumentParser()
parser.add_argument("--subreddit", help="which subreddit to use", default="rickandmorty")
args = parser.parse_args()
subreddit = args.subreddit
# Login to Reddit
reddit_account = praw.Reddit(secret_keys.reddit_bot_user_agent)
reddit_account.login(username=secret_keys.reddit_username,password=secret_keys.reddit_user_password)

upload_queue = []
upload_timer = time.time()
upload_timeout = 60*10

def verbose_print(msg,verbose = False):
    if verbose:
        print msg

def check_condition(c):
    text = c.body
    tokens = text.lower().split()
    if len(tokens)  == 1 and ("stylizebot" in tokens):
        return True

def bot_action(c, verbose=True):
    if not database.did_reply_thread(c.link_id):
        img_url = c.link_url
        stylized_image_url = ""

        if len(stylized_image_url) == 0:
            print 'From bot action :: There was an error while trying to colorize and upload the photo , %s' % img_url
            return ''

        #Reply to the one who summned the bot
        elif 'already_stylized' in stylized_image_url:
            msg = 'Hi I\'m stylizebot. I was trained to stylize photos.\n\n Your photo seems to be already stylized, Please try uploading another photo. \n\n This is still a **beta-bot**.'
        else:
            msg = 'Hi I\'m stylizebot. I was trained to stylize photos.\n\n This is my attempt to stylize your image, here you go : %s \n\n This is still a **beta-bot**. '%(stylized_image_url)
    else:
        stylized_image_url = image_downloader.get_secret_image_url()
        msg = 'Hi I\'m stylizebot. \n\n It seems this photo has been requested to be stylized already. '%(stylized_image_url)
    try:
        res = c.reply(msg)
        database.add_thread(c.link_id,c.link_url,stylized_image_url)
        database.add_comment(c.id)
    except:
        upload_queue.append((c,msg))
        traceback.print_exc()

def handle_private_msg(msg,verbose=True):

    if database.did_reply_comment(msg.id):
        return

    urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', msg.body)
    for url in urls:
        print 'URL from msg: ',url
        stylized_image_url = colorize_and_upload_from_url(url)

        if len(stylized_image_url) == 0 or 'already_stylized' in stylized_image_url:
            msg.mark_as_read()
            print 'From Private msg :: There was an error while trying to colorize and upload the photo , %s',url
            return ''
        msg_to_send = 'Hi I\'m stylizebot.\n\n This is my attempt to stylize your image, here you go : %s \n\n This is still a **beta-bot**. '%(stylized_image_url)
        try:
            res = msg.reply(msg_to_send)
            msg.mark_as_read()
            database.add_comment(msg.id)
        except:
            traceback.print_exc()

def run_main_reddit_loop():
    global praw,database,upload_timer

    #Main loop the listens to new comments on some subreddit
    for c in praw.helpers.comment_stream(reddit_account, subreddit):
        if check_condition(c):
            if not database.did_reply_comment(c.id):
                submission = reddit_account.get_submission(submission_id=c.permalink)
                flat_comments = praw.helpers.flatten_tree(submission.comments)
                already_commented = False
                for comment in flat_comments:
                    if str(comment.author) == secret_keys.reddit_username:
                        database.add_comment(c.id)
                        database.add_thread(c.link_id,c.link_url,'')
                        already_commented = True
                        break
                if not already_commented:
                    bot_action(c)
        if (time.time() - upload_timer)  > upload_timeout :
            upload_timer = time.time()
            print "Trying to send a comment"
            try:
                reddit_comment,msg = upload_queue[0]
                print reddit_comment.permalink,msg
                reddit_comment.reply(msg)
                upload_queue.pop()
            except:
                pass

        for msg in reddit_account.get_unread(limit=None):
            if msg.new and len(msg.context) == 0:
                handle_private_msg(msg)

while True:
    try:
        run_main_reddit_loop()
    except:
        traceback.print_exc()
        reddit_account = praw.Reddit(secret_keys.reddit_bot_user_agent)
        reddit_account.login(username=secret_keys.reddit_username,password=secret_keys.reddit_user_password)
