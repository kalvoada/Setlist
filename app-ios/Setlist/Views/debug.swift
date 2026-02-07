//
//  debug.swift
//  Setlist
//
//  Created by Adam Kalvoda on 06.02.2026.
//
import SwiftUI

struct DebugView: View {
    @State private var message: String = "Loading..."

    var body: some View {
        Text(message)
            .font(.title)
            .padding()
            .onAppear {
                fetchMessage()
            }
    }

    func fetchMessage() {
        guard let url = URL(string: "http://127.0.0.1:8000/hello") else {
            return
        }

        URLSession.shared.dataTask(with: url) { data, _, error in
            if let data = data,
               let decoded = try? JSONDecoder().decode(Response.self, from: data) {
                DispatchQueue.main.async {
                    message = decoded.message
                }
            } else {
                DispatchQueue.main.async {
                    message = "Failed to load 😢"
                }
            }
        }.resume()
    }
}



struct Response: Decodable {
    let message: String
}
