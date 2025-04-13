import LLM_api
from database import ImageDB
from PIL import Image
print("hi")
def main():
    imDB = ImageDB()
    llm = LLM_api.DeepSeekLLM()

    history = []

    while True:
        prompt = input("user input:")#"你說的對，但是\nルビィちゃん🍭はーい！🙋🏻‍♀️なにが好き❓チョコミント🍫🍃よりも💖あ♡な♡た💖歩夢ちゃん🐰はーい！🙋🏻‍♀️何が好き❓ストロベリーフレイバー🍓よりも💖あ♡な♡た💖四季ちゃん🧪はーい！🙋🏻‍♀️何が好き❓クッキー&クリーム🍪🧁よりも💖あ♡な♡た💖みんな📢はーい！！🙋🏻‍♀️何が好き❓モチロン😈大好き😻AiScReam🍨🍦"
        if prompt == "<end>":
            break
        print("Response:")
        response, history = llm.stream_by_sentence(prompt, history=history)
        #print("response", response)
        try:
            for response_chunk in response:
                print(response_chunk)
                output = imDB.find_matches(response_chunk)
                img = Image.open(output[0][0])
                # Display the image
                img.show()
                #print("matched", output)  # Stream response to console
                #yield output
        except Exception as e:
            print(f"Error in main(): {e}")


if __name__ == "__main__":
    main()