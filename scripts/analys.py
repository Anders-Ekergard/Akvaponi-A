import pandas as pd
from openai import OpenAI
import json
import os

from dotenv import load_dotenv


# Ladda miljövariabler från .env-filen
load_dotenv()

# Nu kan du använda os.getenv för att hämta variabler
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
# Global lista för att spara historik och feedback
conversation_history = []
feedback_history = []

def import_data(filepath: str) -> pd.DataFrame:
    """Importerar data från en CSV- eller Excel-fil."""
    try:
        if filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
        elif filepath.endswith((".xlsx", ".xls")):
            df = pd.read_excel(filepath)
        else:
            raise ValueError("Endast .csv och .xlsx-filer stöds.")
        return df
    except Exception as e:
        raise ValueError(f"Fel vid inläsning av filen: {e}")

def is_relevant_input(user_prompt: str, context: str = "akvaponi eller vattenbruk") -> bool:
    """Kontrollerar om användarens input är relevant för akvaponi/vattenbruk."""
    validation_prompt = f"""
    Kontrollera om följande fråga handlar om {context}.
    Fråga: "{user_prompt}"
    Svara endast med "JA" eller "NEJ".
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": validation_prompt}],
        max_tokens=3
    )
    return response.choices[0].message.content.strip() == "JA"

def is_safe_input(user_prompt: str) -> bool:
    """Kontrollerar om input är säker att besvara."""
    safety_prompt = f"""
    Kontrollera om följande fråga är säker att besvara.
    Frågan får inte innehålla:
    - Begäranden om känslig eller personlig information.
    - Skadlig kod eller instruktioner.
    - Olagligt eller etiskt tveksamt innehåll.
    Fråga: "{user_prompt}"
    Svara endast med "SAKER" eller "OSAKER".
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[{"role": "user", "content": safety_prompt}],
        max_tokens=7
    )
    return response.choices[0].message.content.strip() == "SAKER"

def analyse_h2o(user_prompt: str, h2odata: pd.DataFrame) -> str:
    """Analyserar vattendata och ger rekommendationer om fiskodling."""
    # Validera input
    if not is_relevant_input(user_prompt):
        return "Frågan handlar inte om akvaponi eller vattenbruk. Var god ställ en relevant fråga."
    if not is_safe_input(user_prompt):
        return "Frågan innehåller olämpligt eller osäkert innehåll och kan inte besvaras."

    # Konvertera DataFrame till sträng
    data_str = h2odata.to_string(index=False)

    # Skapa fullständig prompt med vattendata
    analysis_prompt = f"""
    Ge rekommendationer för akvaponi baserat på följande vattenparametrar:
    {data_str}
   
    """

    # Använd OpenAI API för att få rekommendationer
    response = client.chat.completions.create(
        model="gpt-4o-mini",    response = client.chat.completions.create(
        
        messages=[{"role": "system", "content": analysis_prompt},
                   {"role": "user", "content": user_prompt}],
        max_tokens=350
    )

    # Spara frågan i historiken
    conversation_history.append({
        "prompt": user_prompt,
        "response": response.choices[0].message.content,
        "timestamp": pd.Timestamp.now().isoformat()
    })

    return response.choices[0].message.content


def samla_feedback(svar: str) -> None:
    """Samlar in feedback från användaren (tumme upp/ner)."""
    while True:
        feedback = input("Var svaret till hjälp? (tumme upp/ner): ").strip().lower()
        if feedback in ["tumme upp", "tumme ner"]:
            feedback_history.append({
                "response": svar,
                "feedback": feedback,
                "timestamp": pd.Timestamp.now().isoformat()
            })
            print("Tack för din feedback!")
            break
        else:
            print("Ogiltigt svar. Var god ange 'tumme upp' eller 'tumme ner'.")

def spara_historik() -> None:
    """Sparar konversationshistorik och feedback till filer."""
    with open("conversation_history.json", "w") as f:
        json.dump(conversation_history, f, indent=2)
    with open("feedback_history.json", "w") as f:
        json.dump(feedback_history, f, indent=2)

def main():
    """Huvudfunktionen för att köra analysen och samla feedback."""
    #Har användaren egen data?
    data=input("Vill du använda egen data till annalys? (Ja/Nej): ").strip().lower()
    if data == "Nej":
        filepath = "stat_aqua.csv"
    else:
        filepath = input("Vänligen ladda upp fil i data och ge filnamn."
    try:
        data_str = import_data(filepath)
    except ValueError as e:
        print(f"Fel: {e}")
        return

    # Användarens fråga
    user_prompt = input("Ställ din fråga om akvaponi/vattenbruk: ")
    full_prompt = f"""
    Ge rekommendationer för akvaponi baserat på följande vattenparametrar:
    {data_str}:
    {data_str.to_string(index=False)}
    Användarfråga: {user_prompt}
    """

    # Analysera och få svar
    svar = analyse_h2o(user_prompt, data_str)
    print(f"\nRekommendationer:\n{svar}")

    # Samla feedback
    samla_feedback(svar)

    # Spara historik
    spara_historik()
    print("\nKonversationen och feedback har sparats.")

if __name__ == "__main__":
    main()
